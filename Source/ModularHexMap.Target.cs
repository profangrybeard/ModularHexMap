// Copyright (c) 2026. All rights reserved.

using UnrealBuildTool;
using System.Collections.Generic;

public class ModularHexMapTarget : TargetRules
{
	public ModularHexMapTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.Add("ModularHexMap");
	}
}
