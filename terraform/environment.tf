provider "aws" {
  region = "${var.aws_region}"
}

resource "aws_key_pair" "deployer_key" {
  key_name   = "deployer_key"
  public_key = file("${path.module}/deployer_key.pub")
}
