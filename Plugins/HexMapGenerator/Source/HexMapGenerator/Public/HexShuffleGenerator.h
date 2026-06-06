// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HexMapGrowthLibrary.h"
#include "HexShuffleGenerator.generated.h"

class UHexTileSet;
class UHexCoreLayout;
class UInstancedStaticMeshComponent;
class UStaticMesh;
class UTextRenderComponent;
class ASplineRoad;

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

	/** Hardwired fixed core (The Pit's town center): bespoke tiles placed verbatim at their axial
	 *  coords; the procedural frontier grows around them. Leave null to use the placeholder core. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle")
	TObjectPtr<UHexCoreLayout> CoreLayout;

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

	/** Filename (in Design/Rolls, .json optional) or a full path, to reload with Load Roll. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Rolls")
	FString RollToLoad;

	/** Save the current layout to Design/Rolls/Roll_seed<N>_vac<V>.json (the durable record). */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle|Rolls")
	void SaveRoll();

	/** Reload the roll named by RollToLoad and rebuild it verbatim (no re-growth). */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle|Rolls")
	void LoadRoll();

	/** Module mesh extruded along the road splines (assign SM_RoadSeg). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Spline Roads")
	TObjectPtr<UStaticMesh> RoadSegmentMesh;

	/** Review mode: Randomize drops a plain hex (GroundMesh) per cell instead of the road
	 *  tiles, so the curved spline roads read clean and the empty hexes show the blocks. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Spline Roads")
	bool bGroundOnly = false;

	/** Plain hex placed per cell when bGroundOnly (assign SM_GroundHex). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Spline Roads")
	TObjectPtr<UStaticMesh> GroundMesh;

	/** Z (uu) the road splines sit at — match the tile carriageway top (TOP = 0.5 m = 50). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Spline Roads")
	float SplineRoadZ = 50.f;

	/** Trace the last grown network into chains and spawn one curved ASplineRoad per chain. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle|Spline Roads")
	void BuildSplineRoads();

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

	// The last network Build() placed — what SaveRoll writes out.
	UPROPERTY(Transient)
	FHexNetwork LastNetwork;

	// Spawned curved-road actors (one per traced chain); destroyed on Clear / rebuild.
	UPROPERTY(Transient)
	TArray<TObjectPtr<ASplineRoad>> SplineRoads;
	void ClearSplineRoads();

	void MeasureCalibration();
	int32 MeasureTileMask(UStaticMesh* Mesh) const;
	bool FindPlacement(int32 CellMask, int32& OutTile, int32& OutYawSteps) const;

	void Build(const FHexNetwork& Net);
	UInstancedStaticMeshComponent* GetOrCreateISM(UStaticMesh* Mesh);
};
