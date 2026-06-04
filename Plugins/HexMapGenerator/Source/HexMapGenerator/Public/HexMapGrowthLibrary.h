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

	/** Region size in hex rings around the origin. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0"))
	int32 Radius = 3;

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

	/** Max secondary road segments to branch off the arteries. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0"))
	int32 RoadBudget = 40;

	/** Chance to sprout a branch to either side while extending. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0", ClampMax = "1"))
	float BranchChance = 0.25f;

	/** Bias toward continuing straight through a cell. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Growth", meta = (ClampMin = "0", ClampMax = "1"))
	float StraightBias = 0.6f;
};

/** One resolved cell: its axial coordinate and 6-bit road mask. */
USTRUCT(BlueprintType)
struct FHexCellResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Hex Map")
	FIntPoint Axial = FIntPoint::ZeroValue;

	UPROPERTY(BlueprintReadOnly, Category = "Hex Map")
	int32 RoadMask = 0;
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
	UPROPERTY() int32 Vacancies = 0;
	UPROPERTY() FHexGrowthParams Growth;
	UPROPERTY() FHexNetwork Network;
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
