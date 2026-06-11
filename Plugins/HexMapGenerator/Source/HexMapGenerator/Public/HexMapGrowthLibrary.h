// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "HexMapGrowthLibrary.generated.h"

/** Tunables for road-driven growth. */
USTRUCT(BlueprintType)
struct FHexGrowthParams
{
	GENERATED_BODY()

	/** Region size in hex rings around the origin. Needs headroom past the core (~ring 2) for
	 *  the arteries to bend through — keep it well above ArteryStraightRadius. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0"))
	int32 Radius = 6;

	/** Fixed-core radius: cells with Distance <= this are PINNED (the Pit + story ring) and the
	 *  generator grows the frontier *around* them rather than through them. 0 = no core. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0"))
	int32 CoreRadius = 1;

	/** Lay a straight backbone road along each hex axis, center -> map edge. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth")
	bool bCardinalArteries = true;

	/** How many of the 3 hex axes get a backbone artery (0-3). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0", ClampMax = "3"))
	int32 NumArteries = 3;

	/** Max secondary road segments to branch off the arteries.
	 *  Defaults = the blessed ShuffleLab tuning (2026-06 sweep: 120 frontier souls,
	 *  0 unresolved over 200 rolls) so a fresh generator rolls a real town. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0"))
	int32 RoadBudget = 174;

	/** Chance to sprout a branch to either side while extending. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0", ClampMax = "1"))
	float BranchChance = 0.21f;

	/** Base bias toward continuing straight through a cell (before run-length decay). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0", ClampMax = "1"))
	float StraightBias = 0.72f;

	/** Stacking turn pressure: each consecutive straight segment multiplies the straight-continue
	 *  chance by this, so long straight runs grow increasingly likely to kink — built-in
	 *  visibility blocking. 1 = no decay (constant straightness); lower = turns sooner. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0", ClampMax = "1"))
	float StraightDecay = 0.8f;

	/** Hard cap on consecutive straight segments before a turn is forced (0 = no cap, rely on
	 *  decay only). A guaranteed sightline limit for level design. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0"))
	int32 MaxStraightRun = 0;

	/** Cardinal arteries run dead-straight out to this ring (a legible spine off the core), then
	 *  begin to bend and divide so the avenue reads as intentional, not a straight ray. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth|Arteries", meta = (ClampMin = "0"))
	int32 ArteryStraightRadius = 3;

	/** Past ArteryStraightRadius, per-step chance an artery KINKS (turns +/-1) instead of running on. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth|Arteries", meta = (ClampMin = "0", ClampMax = "1"))
	float ArteryKinkChance = 0.35f;

	/** Past ArteryStraightRadius, per-step chance an artery DIVIDES (spawns a diverging branch). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth|Arteries", meta = (ClampMin = "0", ClampMax = "1"))
	float ArteryForkChance = 0.12f;

	/** Roll a river: a boundary-to-boundary momentum walk grown BEFORE roads (water is
	 *  foundation — Docs/Rivers.md). Off = pre-river behavior, bit-exact for the road layer. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth|River")
	bool bRiver = true;

	/** River momentum: chance to continue straight each step (loves crossing, hates
	 *  branching — v1 never branches). Lower = lazier meander. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth|River", meta = (ClampMin = "0", ClampMax = "1"))
	float RiverStraightBias = 0.8f;

	/** The player's river choice at destiny-roll time: the OUTFLOW heading (0-5;
	 *  -1 = rolled from the seed). The river is CORE-ANCHORED through-flow: it enters
	 *  from the map edge, passes the wound through two adjacent ring-1 story tiles
	 *  (the authored pour-in — the Pit drinks a spill), and exits along this heading.
	 *  "Players grow the river in a direction they prefer" (director, 2026-06-11). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth|River", meta = (ClampMin = "-1", ClampMax = "5"))
	int32 RiverOutflowDir = -1;
};

/** One resolved cell: its axial coordinate and the layered 6-bit edge masks.
 *  Layers are PARALLEL, never merged (Docs/Rivers.md §2): road and water each keep
 *  binary-necklace math; a cell with both nonzero is a bridge. */
USTRUCT(BlueprintType)
struct FHexCellResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Hex Map")
	FIntPoint Axial = FIntPoint::ZeroValue;

	UPROPERTY(BlueprintReadOnly, Category = "Hex Map")
	int32 RoadMask = 0;

	/** Water layer (0 = dry). Old saved rolls lack the field and load as 0. */
	UPROPERTY(BlueprintReadOnly, Category = "Hex Map")
	int32 WaterMask = 0;
};

/** The grown network: every cell in the region with its road mask (0 = blank). */
USTRUCT(BlueprintType)
struct FHexNetwork
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Hex Map")
	TArray<FHexCellResult> Cells;
};

/**
 * A saved roll — the durable record of a layout we liked. The `Network` (axial + road mask per
 * cell) is the ground truth and reloads verbatim via Build(), immune to later generator edits;
 * `Seed`/`Growth` are kept as provenance (re-tune from here). Serialized to JSON in Design/Rolls.
 */
USTRUCT(BlueprintType)
struct FHexRoll
{
	GENERATED_BODY()

	UPROPERTY() int32 SchemaVersion = 1;
	UPROPERTY() int32 Seed = 0;
	UPROPERTY() FHexGrowthParams Growth;
	UPROPERTY() FHexNetwork Network;

	/** Souls already home (restored cell coords). With Network this makes the roll the
	 *  complete town save: the destiny + how far it has healed. Old rolls lack the
	 *  field and load as empty (nothing restored). */
	UPROPERTY() TArray<FIntPoint> Restored;
};

/**
 * Pure, seeded road-network growth — the reusable core (authoring shuffle now;
 * autofill / gameplay "rearrange" later). No engine-world dependencies.
 */
UCLASS()
class HEXMAPGENERATOR_API UHexMapGrowthLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Grow a connected road network outward from the origin, around a fixed core.
	 * Deterministic per Seed. `CoreCells` are PINNED — their masks are written verbatim and never
	 * mutated; arteries seed from the core boundary (ring CoreRadius+1) so the frontier connects to
	 * the core's exposed road stubs by construction. Pass an empty array to grow with no core
	 * (legacy behavior when Params.CoreRadius == 0).
	 */
	UFUNCTION(BlueprintCallable, Category = "Hex Map")
	static FHexNetwork GrowRoadNetwork(const FHexGrowthParams& Params, const TArray<FHexCellResult>& CoreCells, int32 Seed);

	/**
	 * Build a placeholder fixed core (Pit + ring 1) for testing before the authored layout asset
	 * exists: the Pit (0,0) is blank (a terminus — roads dead-end at its rim); each ring-1 cell on
	 * a chosen artery axis carries a straight road (inward toward the Pit + outward to the frontier).
	 */
	UFUNCTION(BlueprintCallable, Category = "Hex Map")
	static TArray<FHexCellResult> MakePlaceholderCore(const FHexGrowthParams& Params);
};
