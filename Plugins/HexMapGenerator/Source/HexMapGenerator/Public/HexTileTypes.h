// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "HexTileTypes.generated.h"

class UStaticMesh;

/** What a hex edge presents to its neighbor. Extend deliberately (road class, frontage...). */
UENUM(BlueprintType)
enum class EHexEdgeSocket : uint8
{
	Pavement,
	Road
};

/**
 * One tile type in the catalog. Edges are the 6 sockets at rotation 0;
 * edge 0 = +Y (forward), counter-clockwise 1..5 (matches the tile contract).
 */
USTRUCT(BlueprintType)
struct FHexTileDef
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile")
	FName Name;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile")
	TSoftObjectPtr<UStaticMesh> Mesh;

	/** Exactly 6 entries; index = edge. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile", meta = (EditFixedSize))
	TArray<EHexEdgeSocket> Edges;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile", meta = (ClampMin = "0"))
	int32 Weight = 1;

	/** How many people this section can house (rescue capacity / vacancies). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile", meta = (ClampMin = "0"))
	int32 Occupancy = 0;

	FHexTileDef()
	{
		Edges.Init(EHexEdgeSocket::Pavement, 6);
	}
};
