// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "HexTileTypes.h"
#include "HexTileSet.generated.h"

struct FRandomStream;

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

	/** Find a tile + rotation (0..5) whose rotated ROAD and WATER masks BOTH equal the
	 *  targets under the same rotation (the layered-mask contract — Docs/Rivers.md §2).
	 *  TargetWaterMask 0 = a dry cell, matched by dry tiles only.
	 *  When several catalog tiles resolve to the same masks (blank variants),
	 *  VariantStream picks among them by FHexTileDef::Weight and rolls a free heading
	 *  for mask-0 tiles; null keeps the legacy first-match (tools, previews). */
	bool FindTileForMask(int32 TargetMask, int32 TargetWaterMask, int32& OutTileIndex, int32& OutRotation,
		const FRandomStream* VariantStream = nullptr) const;

	/** Shared weighted pick over parallel candidate arrays (used by both the authored
	 *  resolver above and the generator's measured FindPlacement). Returns an index
	 *  into Weights: candidate 0 when Stream is null or all weight is gone (legacy
	 *  determinism), else a Weight-proportional draw from Stream. */
	static int32 PickWeightedCandidate(TArrayView<const float> Weights, const FRandomStream* Stream);
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
