output "instance_ips" {
  value = aws_instance.cluster.*.public_ip
}
