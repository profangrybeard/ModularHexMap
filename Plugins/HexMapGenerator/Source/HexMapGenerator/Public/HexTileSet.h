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
