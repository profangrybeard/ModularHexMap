// Copyright (c) 2026. All rights reserved.

using UnrealBuildTool;

public class HexMapGeneratorEditor : ModuleRules
{
	public HexMapGeneratorEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
			"HexMapGenerator",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"Slate",
			"SlateCore",
			"UnrealEd",
			"EditorStyle",
			"EditorWidgets",
			"EditorSubsystem",
			"ToolMenus",
			"InputCore",
			"Projects",
		});
	}
}
