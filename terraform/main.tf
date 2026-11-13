# ------------------------------------------------------------------------------
# hold-my-beer voting host: one small OCI instance, the app behind a Cloudflare
# Tunnel. Inbound only SSH from admin_cidrs; the app is reached via the tunnel.
# Runbook: docs/runbook-terraform-host.md
# ------------------------------------------------------------------------------

provider "oci" {
  config_file_profile = var.oci_profile
  region              = var.region
}

# token from the environment: CLOUDFLARE_API_TOKEN (make tf-* injects it via op run)
provider "cloudflare" {}

locals {
  fqdn   = "${var.hostname}.${var.zone}"
  region = { "eu-zurich-1" = "zrh", "eu-frankfurt-1" = "fra", "us-ashburn-1" = "iad" }[var.region]
  suffix = "${local.region}-${var.env}-hmb"
  tags = {
    project = "hold-my-beer"
    host    = local.fqdn
  }
}

# -- Network -------------------------------------------------------------------
resource "oci_core_vcn" "this" {
  compartment_id = var.compartment_ocid
  cidr_blocks    = [var.vcn_cidr]
  display_name   = "vcn-${local.suffix}-net-${var.instance_no}"
  dns_label      = "hmb${var.instance_no}"
  freeform_tags  = local.tags
}

resource "oci_core_internet_gateway" "this" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "igw-${local.suffix}-net-${var.instance_no}"
  freeform_tags  = local.tags
}

resource "oci_core_route_table" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "rt-${local.suffix}-public-${var.instance_no}"
  freeform_tags  = local.tags

  route_rules {
    destination       = "0.0.0.0/0"
    network_entity_id = oci_core_internet_gateway.this.id
  }
}

resource "oci_core_security_list" "public" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.this.id
  display_name   = "sl-${local.suffix}-public-${var.instance_no}"
  freeform_tags  = local.tags

  # outbound: dnf, pip, Cloudflare edge (TCP 443, http2)
  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  dynamic "ingress_security_rules" {
    for_each = var.admin_cidrs
    content {
      source      = ingress_security_rules.value
      protocol    = "6"
      description = "SSH from admin"
      tcp_options {
        min = 22
        max = 22
      }
    }
  }

  # path MTU discovery
  ingress_security_rules {
    source   = "0.0.0.0/0"
    protocol = "1"
    icmp_options {
      type = 3
      code = 4
    }
  }
}

resource "oci_core_subnet" "public" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.this.id
  cidr_block        = var.vcn_cidr
  display_name      = "subnet-${local.suffix}-public-${var.instance_no}"
  dns_label         = "pub"
  route_table_id    = oci_core_route_table.public.id
  security_list_ids = [oci_core_security_list.public.id]
  freeform_tags     = local.tags
}

# -- Cloudflare tunnel (locally managed: ingress lives in /etc/cloudflared) -----
data "cloudflare_zone" "this" {
  filter = {
    name = var.zone
  }
}

resource "random_bytes" "tunnel_secret" {
  length = 32
}

resource "cloudflare_zero_trust_tunnel_cloudflared" "this" {
  account_id    = data.cloudflare_zone.this.account.id
  name          = var.hostname
  config_src    = "local"
  tunnel_secret = random_bytes.tunnel_secret.base64
}

resource "cloudflare_dns_record" "this" {
  zone_id = data.cloudflare_zone.this.zone_id
  name    = local.fqdn
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.this.id}.cfargotunnel.com"
  proxied = true
  ttl     = 1
  comment = "hold-my-beer voting app (terraform)"
}

# -- Instance ------------------------------------------------------------------
data "oci_identity_availability_domains" "ads" {
  compartment_id = var.compartment_ocid
}

data "oci_core_images" "ol9" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Oracle Linux"
  operating_system_version = "9"
  shape                    = var.shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
  state                    = "AVAILABLE"
}

locals {
  # skip GPU / special builds, take the newest plain OL9 image for the shape
  image_id = [for i in data.oci_core_images.ol9.images : i.id if !can(regex("GPU|Minimal", i.display_name))][0]

  cloud_init = templatefile("${path.module}/templates/cloud-init.yaml.tftpl", {
    fqdn      = local.fqdn
    app_port  = var.app_port
    tunnel_id = cloudflare_zero_trust_tunnel_cloudflared.this.id
    credentials = jsonencode({
      AccountTag   = data.cloudflare_zone.this.account.id
      TunnelID     = cloudflare_zero_trust_tunnel_cloudflared.this.id
      TunnelSecret = random_bytes.tunnel_secret.base64
    })
  })
}

resource "oci_core_instance" "this" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  display_name        = "vm-${local.suffix}-app-${var.instance_no}"
  shape               = var.shape
  freeform_tags       = local.tags

  shape_config {
    ocpus         = var.ocpus
    memory_in_gbs = var.memory_gb
  }

  source_details {
    source_type             = "image"
    source_id               = local.image_id
    boot_volume_size_in_gbs = var.boot_volume_gb
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.public.id
    assign_public_ip = true
    hostname_label   = var.hostname
  }

  metadata = {
    ssh_authorized_keys = trimspace(file(pathexpand(var.ssh_public_key_path)))
    user_data           = base64encode(local.cloud_init)
  }

  instance_options {
    are_legacy_imds_endpoints_disabled = true
  }

  lifecycle {
    # a newer OL9 image must not replace the running host
    ignore_changes = [source_details[0].source_id]
  }
}
