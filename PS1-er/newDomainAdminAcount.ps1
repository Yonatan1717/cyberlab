$username = Read-Host "Enter username for new domain admin account"
$password = Read-Host -AsSecureString "Enter password for $username"
$confirmPassword = Read-Host -AsSecureString "Confirm password for $username"
$plain = [System.Net.NetworkCredential]::new('', $password).Password
$plainConfirm = [System.Net.NetworkCredential]::new('', $confirmPassword).Password
if ($plain -cne $plainConfirm) {
    Write-Host "Passwords do not match. Exiting."
    exit
}
$domain = Read-Host "Enter the domain for the new user" # ekse corp.nvidia.test
$domainParts = $domain -split '\.'
$domainDN = ($domainParts | ForEach-Object { "DC=$_" }) -join ','
Write-Host "Domain DN: $domainDN"
exit 0

import-module ActiveDirectory

New-ADUser -Name $username -SamAccountName $username -AccountPassword $password -Enabled $true -PasswordNeverExpires $true -ChangePasswordAtLogon $false -Path "CN=Users,$domainDN"

Add-ADGroupMember -Identity "Domain Admins" -Members $username
