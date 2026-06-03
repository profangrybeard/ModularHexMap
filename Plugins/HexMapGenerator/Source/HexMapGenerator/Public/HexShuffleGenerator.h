// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HexMapGrowthLibrary.h"
#include "HexShuffleGenerator.generated.h"

class UHexTileSet;
class UInstancedStaticMeshComponent;
class UStaticMesh;
class UTextRenderComponent;

/**
 * Grows a road network and drops the real tiles into the level (one ISM per mesh),
 * resolving rotation against each tile's TRUE imported geometry (auto-measured), so
 * carriageways actually connect regardless of glTF axis/handedness quirks. Hit
 * "Randomize" in Details to reroll under real lighting. Runtime-callable.
 */
UCLASS()
class HEXMAPGENERATOR_API AHexShuffleGenerator : public AActor
{
	GENERATED_BODY()

public:
	AHexShuffleGenerator();

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle")
	TObjectPtr<UHexTileSet> TileSet;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle")
	int32 Seed = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle")
	FHexGrowthParams Growth;

	/** Hex circumradius in UE units (R = 5 m -> 500). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle")
	float HexCircumradiusUU = 500.f;

	/** Rough rescue capacity of the current layout (sum of placed tiles' Occupancy). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Hex Shuffle")
	int32 EstimatedVacancies = 0;

	/** Measure each tile's real road edges from its geometry (immune to import orientation). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Calibration")
	bool bAutoCalibrate = true;

	/** Optional manual yaw nudge added to every tile (normally 0 once auto-calibrated). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Calibration")
	float ExtraYawDeg = 0.f;

	/** Flip if turns/curves come out mirrored (accounts for UE's yaw direction). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Calibration")
	bool bInvertYawShift = false;

	/** Reroll: grow a fresh network and rebuild the tiles. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle")
	void Randomize();

	/** Re-measure tile geometry (call if you re-import or swap tiles). */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle")
	void Recalibrate();

	/** Remove all spawned tiles. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle")
	void Clear();

private:
	UPROPERTY(VisibleAnywhere, Category = "Hex Shuffle")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, Category = "Hex Shuffle")
	TObjectPtr<UTextRenderComponent> PopLabel;

	UPROPERTY(Transient)
	TMap<TObjectPtr<UStaticMesh>, TObjectPtr<UInstancedStaticMeshComponent>> MeshToISM;

	// Calibration cache: each tile's true road mask (edges its carriageway reaches), at yaw 0.
	UPROPERTY(Transient)
	TArray<int32> TileRealMask;
	bool bCalibrated = false;

	void MeasureCalibration();
	int32 MeasureTileMask(UStaticMesh* Mesh) const;
	bool FindPlacement(int32 CellMask, int32& OutTile, int32& OutYawSteps) const;

	void Build(const FHexNetwork& Net);
	UInstancedStaticMeshComponent* GetOrCreateISM(UStaticMesh* Mesh);
};
