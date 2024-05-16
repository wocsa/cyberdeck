resource "aws_vpc" "main" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support = true
  enable_dns_hostnames = true

  tags = {
    Name = "${var.project_name}-${var.git_branch_name}-vpc"
    Project = "${var.project_name}"
    GitBranch = "${var.git_branch_name}"
    CommitNumber = "${var.commit_number}"
  }
}

resource "aws_subnet" "main" {
  vpc_id     = aws_vpc.main.id
  cidr_block = "10.0.1.0/24"
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.project_name}-${var.git_branch_name}-subnet"
    Project = "${var.project_name}"
    GitBranch = "${var.git_branch_name}"
    CommitNumber = "${var.commit_number}"
  }
}

resource "aws_internet_gateway" "gw" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "${var.project_name}-${var.git_branch_name}-igw"
    Project = "${var.project_name}"
    GitBranch = "${var.git_branch_name}"
    CommitNumber = "${var.commit_number}"
  }
}

resource "aws_route_table" "main" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.gw.id
  }

  tags = {
    Name = "${var.project_name}-${var.git_branch_name}-rtb"
    Project = "${var.project_name}"
    GitBranch = "${var.git_branch_name}"
    CommitNumber = "${var.commit_number}"
  }
}

resource "aws_route_table_association" "main" {
  subnet_id      = aws_subnet.main.id
  route_table_id = aws_route_table.main.id
}
