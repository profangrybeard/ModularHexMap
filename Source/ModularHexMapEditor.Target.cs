// Copyright (c) 2026. All rights reserved.

using UnrealBuildTool;
using System.Collections.Generic;

public class ModularHexMapEditorTarget : TargetRules
{
	public ModularHexMapEditorTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Editor;
		DefaultBuildSettings = BuildSettingsVersion.Latest;
		IncludeOrderVersion = EngineIncludeOrderVersion.Latest;
		ExtraModuleNames.AddRange(new string[] { "ModularHexMap", "TP_ThirdPerson" });
	}
}
