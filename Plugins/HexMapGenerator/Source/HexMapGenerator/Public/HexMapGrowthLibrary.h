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
 * Pure, seeded road-network growth — the reusable core (authoring shuffle now;
 * autofill / gameplay "rearrange" later). No engine-world dependencies.
 */
UCLASS()
class HEXMAPGENERATOR_API UHexMapGrowthLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** Grow a connected road network outward from the origin. Deterministic per Seed. */
	UFUNCTION(BlueprintCallable, Category = "Hex Map")
	static FHexNetwork GrowRoadNetwork(const FHexGrowthParams& Params, int32 Seed);
};
