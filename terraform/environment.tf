provider "aws" {
  region = "us-west-2"
}

variable "instance_count" {
  default = 3
}

resource "aws_key_pair" "deployer_key" {
  key_name   = "deployer_key"
  public_key = file("${path.module}/deployer_key.pub")
}
