output "url" {
  description = "Public URL (PUBLIC_BASE_URL = VOTING_URL)"
  value       = "https://${local.fqdn}"
}

output "public_ip" {
  value = oci_core_instance.this.public_ip
}

output "instance_name" {
  value = oci_core_instance.this.display_name
}

output "tunnel_id" {
  value = cloudflare_zero_trust_tunnel_cloudflared.this.id
}

output "ssh_config" {
  description = "Block for ~/.ssh/config.d/ (make tf-ssh-config writes it)"
  value       = <<-EOT
    # ${local.fqdn}: DNS points to Cloudflare (tunnel), SSH goes to the instance IP
    Host ${var.hostname} ${local.fqdn}
      HostName ${oci_core_instance.this.public_ip}
      User opc
      IdentityFile ${var.ssh_public_key_path}
      IdentitiesOnly yes
  EOT
}
