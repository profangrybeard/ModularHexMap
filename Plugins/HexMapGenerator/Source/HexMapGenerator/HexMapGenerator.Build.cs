// Copyright (c) 2026. All rights reserved.

using UnrealBuildTool;

public class HexMapGenerator : ModuleRules
{
	public HexMapGenerator(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"Slate",
			"SlateCore",
			"Json",          // roll save/load (FJsonObjectConverter)
			"JsonUtilities",
			"MeshDescription",        // MeasureTileMask reads SOURCE geometry —
			"StaticMeshDescription",  // render LOD0 is presentation (Nanite
			                          // fallback / LOD reduction decimates it;
			                          // the 0x00-water hunt, 2026-06-12)
		});
	}
}
