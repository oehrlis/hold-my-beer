# -- OCI -----------------------------------------------------------------------
variable "oci_profile" {
  description = "Profile in ~/.oci/config"
  type        = string
  default     = "ACE"
}

variable "region" {
  description = "OCI region"
  type        = string
  default     = "eu-zurich-1"
}

variable "compartment_ocid" {
  description = "Compartment for network and instance (set in terraform.tfvars, never committed)"
  type        = string
}

variable "admin_cidrs" {
  description = "Source CIDRs allowed to reach SSH (e.g. [\"203.0.113.10/32\"]) - nothing else is open inbound"
  type        = list(string)

  validation {
    condition     = length(var.admin_cidrs) > 0 && alltrue([for c in var.admin_cidrs : can(cidrnetmask(c)) && c != "0.0.0.0/0"])
    error_message = "admin_cidrs needs at least one valid CIDR and must not contain 0.0.0.0/0."
  }
}

variable "ssh_public_key_path" {
  description = "Public key for user opc (private key stays in the 1Password SSH agent)"
  type        = string
  default     = "~/.ssh/hmb.oradba.ch.pub"
}

variable "shape" {
  description = "Compute shape - A1.Flex 1 OCPU / 6 GB is inside the Always Free allowance"
  type        = string
  default     = "VM.Standard.A1.Flex"
}

variable "ocpus" {
  type    = number
  default = 1
}

variable "memory_gb" {
  type    = number
  default = 6
}

variable "boot_volume_gb" {
  description = "Boot volume size (OCI minimum 47 GB; Always Free covers 200 GB in total)"
  type        = number
  default     = 50
}

variable "vcn_cidr" {
  type    = string
  default = "10.42.0.0/24"
}

# -- Naming --------------------------------------------------------------------
variable "env" {
  description = "Environment code for resource names (prod | dev | test | lab)"
  type        = string
  default     = "lab"
}

variable "instance_no" {
  description = "Instance suffix for resource names (01, 02, ...)"
  type        = string
  default     = "01"
}

# -- Cloudflare ----------------------------------------------------------------
variable "zone" {
  description = "Cloudflare zone"
  type        = string
  default     = "oradba.ch"
}

variable "hostname" {
  description = "Host label below the zone; also the tunnel name (hmb2 = test/backup, hmb = live)"
  type        = string
  default     = "hmb2"
}

variable "app_port" {
  description = "Local app port behind the tunnel (deploy-public.sh PORT)"
  type        = number
  default     = 8080
}
