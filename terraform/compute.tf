resource "aws_instance" "cluster" {
  count         = var.instance_count
  ami           = var.ami_name
  instance_type = "t4g.micro"  # Adjust as necessary for ARM architecture

  subnet_id              = aws_subnet.main.id
  vpc_security_group_ids = [aws_security_group.allow_ssh.id]
  key_name               = "your-key-name-here"  # Ensure you have this key in your region

  tags = {
    Name = "${var.project_name}-${var.git_branch_name}-instance-${count.index}"
    GitBranch = var.git_branch_name
    CommitNumber = var.commit_number
    Project = var.project_name
  }
}
