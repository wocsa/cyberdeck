resource "aws_security_group" "allow_ssh" {
  name        = "${var.project_name}-${var.git_branch_name}-sg"
  description = "Allow SSH inbound traffic"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.git_branch_name}-sg"
    Project = "${var.project_name}"
    GitBranch = "${var.git_branch_name}"
    CommitNumber = var.commit_number
  }
}
