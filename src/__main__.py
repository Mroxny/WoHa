import pulumi
import pulumi_azure_native as az

# rg = az.resources.ResourceGroup("win11-rg", location="polandcentral")
rg = az.resources.ResourceGroup("win11-rg", location="swedencentral")

public_ip = az.network.PublicIPAddress(
    "win11-ip",
    resource_group_name=rg.name,
    location=rg.location,
    public_ip_allocation_method="Static",
    sku=az.network.PublicIPAddressSkuArgs(name="Standard")
)

subnet = az.network.Subnet(
    "win11-subnet",
    resource_group_name=rg.name,
    virtual_network_name=az.network.VirtualNetwork(
        "win11-vnet",
        resource_group_name=rg.name,
        location=rg.location,
        address_space=az.network.AddressSpaceArgs(address_prefixes=["10.0.0.0/16"])
    ).name,
    address_prefix="10.0.0.0/24"
)

nsg = az.network.NetworkSecurityGroup(
    "win11-nsg",
    resource_group_name=rg.name,
    location=rg.location,
    security_rules=[
        az.network.SecurityRuleArgs(
            name="allow-rdp",
            priority=1000,
            direction="Inbound",
            access="Allow",
            protocol="Tcp",
            source_address_prefix="*",
            source_port_range="*",
            destination_address_prefix="*",
            destination_port_range="3389",
        ),
        az.network.SecurityRuleArgs(
            name="allow-parsec",
            priority=330,
            direction="Inbound",
            access="Allow",
            protocol="Tcp",
            source_address_prefix="*",
            source_port_range="*",
            destination_address_prefix="*",
            destination_port_range="8000-8010",
        )
    ]
)

nic = az.network.NetworkInterface(
    "win11-nic",
    resource_group_name=rg.name,
    location=rg.location,
    network_security_group=az.network.NetworkSecurityGroupArgs(id=nsg.id),
    ip_configurations=[az.network.NetworkInterfaceIPConfigurationArgs(
        name="win11-ipconfig",
        subnet=az.network.SubnetArgs(id=subnet.id),
        public_ip_address=az.network.PublicIPAddressArgs(id=public_ip.id)
    )]
)

vm = az.compute.VirtualMachine(
    "win11-vm",
    resource_group_name=rg.name,
    location=rg.location,
    # hardware_profile=az.compute.HardwareProfileArgs(vm_size="Standard_NV8as_v4"),
    hardware_profile=az.compute.HardwareProfileArgs(vm_size="Standard_NG8ads_V620_v1"),
    network_profile=az.compute.NetworkProfileArgs(
        network_interfaces=[az.compute.NetworkInterfaceReferenceArgs(id=nic.id)]
    ),
    os_profile=az.compute.OSProfileArgs(
        computer_name="win11vm",
        admin_username="TestAdmin",  # Just for the demo
        admin_password="TestAdmin123",
        windows_configuration=az.compute.WindowsConfigurationArgs(
            enable_automatic_updates=True,
            provision_vm_agent=True
        )
    ),
    storage_profile=az.compute.StorageProfileArgs(
        image_reference=az.compute.ImageReferenceArgs(
            publisher="microsoftwindowsdesktop",
            offer="windows-11",
            sku="win11-24h2-pro",
            version="latest"
            # id="/subscriptions/8ae879e3-5e4e-42be-95ea-37f65a44b839/resourceGroups/gamevm-test-1/providers/Microsoft.Compute/galleries/GP_test_image_gallery/images/GP_test_image"
        ),
        os_disk=az.compute.OSDiskArgs(
            create_option="FromImage",
            managed_disk=az.compute.ManagedDiskParametersArgs(
                storage_account_type="Premium_LRS"
            ),
            disk_size_gb=128
        )
    )
)

az.compute.VirtualMachineExtension("amd-gpu-drivers",
    resource_group_name=rg.name,
    vm_name=vm.name,
    location=rg.location,
    publisher="Microsoft.HpcCompute",
    type="AmdGpuDriverWindows",
    type_handler_version="1.1",
    auto_upgrade_minor_version=True
)

pulumi.export("public_ip", public_ip.ip_address)