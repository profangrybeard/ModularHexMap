// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "Engine/DataTable.h"
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

	/** Optional building overlay placed at the same world transform as the street tile.
	 *  Engine adds a parallel ISM keyed on this mesh; M_BuildingBack material slot is the
	 *  future seam for per-edge "inset on blank-side" alley logic (no re-bake needed).
	 *  Leave null for tiles that don't carry a building (e.g. junction, custom blanks). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile")
	TSoftObjectPtr<UStaticMesh> BuildingMesh;

	/** Exactly 6 entries; index = edge. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile", meta = (EditFixedSize))
	TArray<EHexEdgeSocket> Edges;

	/** Water layer at rotation 0 (bit e set when edge e carries the river). 0 for the
	 *  street kit; nonzero on river tiles; road edges + water bits both nonzero = a
	 *  bridge tile. Authored mirror of what calibration measures from M_Water verts. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Tile", meta = (ClampMin = "0", ClampMax = "63"))
	int32 WaterMask = 0;

	FHexTileDef()
	{
		Edges.Init(EHexEdgeSocket::Pavement, 6);
	}
};


/**
 * One row in a roll-constraints DataTable. Row name is the necklace name
 * (e.g. "junction", "tee_c") matching the 14 mask classes the generator emits.
 * Sentinel values keep the editor UX simple — set the spinner to the sentinel
 * and the bound is ignored:
 *   Min   == 0  => no minimum (i.e. unbounded below; 0 happens to also be a
 *                  legitimate min, but having both "no minimum" and "0 minimum"
 *                  collapse to the same behaviour is fine here)
 *   Max   == -1 => no maximum
 *   Exact == -1 => not an exact-count constraint
 * If Exact >= 0 it overrides Min/Max.
 *
 * Read by Python's roll_diagnostics.constrained_randomize() via the DataTable
 * assigned to AHexShuffleGenerator::RollConstraints. Falls back to
 * Design/RollConstraints/<name>.json when no DataTable is assigned.
 */
USTRUCT(BlueprintType)
struct FHexNecklaceConstraint : public FTableRowBase
{
	GENERATED_BODY()

	/** At least this many of this necklace per roll. 0 = no minimum. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Roll Constraint", meta = (ClampMin = "0"))
	int32 Min = 0;

	/** At most this many of this necklace per roll. -1 = no maximum. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Roll Constraint", meta = (ClampMin = "-1"))
	int32 Max = -1;

	/** Require exactly this many. -1 = not an exact-count constraint.
	 *  Overrides Min/Max when set. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Roll Constraint", meta = (ClampMin = "-1"))
	int32 Exact = -1;
};
