// Copyright (c) 2026. All rights reserved.

using UnrealBuildTool;

public class ModularHexMap : ModuleRules
{
	public ModularHexMap(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
		});
	}
}
