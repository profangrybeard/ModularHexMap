// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "HexTileTypes.h"
#include "HexTileSet.generated.h"

/** Artist-editable catalog of hex tile types. */
UCLASS(BlueprintType)
class HEXMAPGENERATOR_API UHexTileSet : public UDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile Set")
	TArray<FHexTileDef> Tiles;

	/** 6-bit road mask of a tile at rotation 0 (bit e set when edge e is Road). */
	static int32 TileMask(const FHexTileDef& Tile);

	/** Find a tile + rotation (0..5) whose rotated road mask equals TargetMask. */
	bool FindTileForMask(int32 TargetMask, int32& OutTileIndex, int32& OutRotation) const;
};

/** One hardwired fixed-core cell: a bespoke mesh pinned at an axial coord (placed verbatim, yaw 0).
 *  RoadMask = its road edges (6-bit) so the growth pins it and the frontier connects on the right
 *  edges. These bypass the mask resolver entirely — the mesh is authored for this exact spot. */
USTRUCT(BlueprintType)
struct FHexCoreCell
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Core")
	FIntPoint Axial = FIntPoint::ZeroValue;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Core")
	TSoftObjectPtr<UStaticMesh> Mesh;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Core")
	int32 RoadMask = 0;
};

/** The authored fixed core (The Pit's town center): the immovable tiles the generator pins and
 *  grows the procedural frontier around. Built from gen_pit_core's core_layout.json. */
UCLASS(BlueprintType)
class HEXMAPGENERATOR_API UHexCoreLayout : public UDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Core")
	TArray<FHexCoreCell> Cells;
};
