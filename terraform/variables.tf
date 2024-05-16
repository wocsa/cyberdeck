variable "ami_name" {
  description = "Name of the AMI to be used for the EC2 instances"
  type        = string
}

variable "instance_count" {
  description = "Number of EC2 instances to create"
  type        = number
}

variable "git_branch_name" {
  description = "Git branch name to use as a prefix and tag"
  type        = string
}

variable "commit_number" {
  description = "Commit number to use as a prefix and tag"
  type        = string
}

variable "project_name" {
  description = "Project name to tag all resources"
  type        = string
}
