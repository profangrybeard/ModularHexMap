// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "HexMapGrowthLibrary.h"
#include "HexShuffleGenerator.generated.h"

class UDataTable;
class UHexTileSet;
class UHexCoreLayout;
class UInstancedStaticMeshComponent;
class UMaterialInterface;
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

	/** Hardwired fixed core (The Pit's town center): bespoke tiles placed verbatim at their axial
	 *  coords; the procedural frontier grows around them. Leave null to use the placeholder core. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle")
	TObjectPtr<UHexCoreLayout> CoreLayout;

	/** Optional roll-constraints DataTable (rows of FHexNecklaceConstraint, row name =
	 *  necklace name). When assigned, roll_diagnostics.constrained_randomize() reads
	 *  the rules from here instead of Design/RollConstraints/<name>.json. Leave null
	 *  to use the JSON fallback. Designed to be cloned and swapped to experiment with
	 *  different "town flavours" without touching Python. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Constraints")
	TObjectPtr<UDataTable> RollConstraints;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle")
	int32 Seed = 0;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle")
	FHexGrowthParams Growth;

	/** Hex circumradius in UE units. Project scale is R = 10 m -> 1000 (set on the
	 *  ShuffleLab actor instance); the header default is left at 500 so any newly-placed
	 *  generator actor announces itself with an obviously-wrong size rather than silently
	 *  picking a number that may or may not match the project's current scale. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle")
	float HexCircumradiusUU = 500.f;

	/** Souls in the current layout: 1 frontier tile = 1 soul (the Pop One spine).
	 *  Core cells (Distance <= Growth.CoreRadius) are the scar — never counted. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Hex Shuffle")
	int32 Souls = 0;

	/** ESCAPE HATCH ONLY (Resistance #12) — flip if a future importer change makes every
	 *  turn/curve come out mirrored. Calibration itself is always-on (the resolver
	 *  measures real geometry per tile; popcount mismatch falls back to authored
	 *  sockets with a warning). Lives under Advanced so it never reads as a daily knob. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, AdvancedDisplay, Category = "Hex Shuffle|Calibration")
	bool bInvertYawShift = false;

	/** Reroll: advance to the next seed, grow a fresh network, rebuild the tiles. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle")
	void Randomize();

	/** Grow + build the network for EXACTLY this seed (no advance). The contract callers
	 *  rely on: the placed roll is the one this seed grows — Python's constrained
	 *  randomize validates a seed first and must place that same network. */
	UFUNCTION(BlueprintCallable, Category = "Hex Shuffle")
	void BuildFromSeed(int32 InSeed);

	/** Re-measure tile geometry (call if you re-import or swap tiles). */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle")
	void Recalibrate();

	/** Remove all spawned tiles. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle")
	void Clear();

	// --- Restoration (the first playable: destiny roll, witnessed restoration) -------

	/** OFF = the dev shuffle tool (everything places solid, label = Souls). ON = the
	 *  destiny renders as a ghost silhouette; only the core scar + restored cells are
	 *  solid; souls arrive one rescue at a time (RestoreNext / RestoreCell); label =
	 *  Pop <restored+1> / <souls+1> — you are the +1. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Restoration")
	bool bRestorationMode = false;

	/** Translucent override for unrestored ghost tiles (assign M_GhostTile; created by
	 *  Tools/setup_ghost_material.py). Unset = ghosts render with their own materials. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Restoration")
	TObjectPtr<UMaterialInterface> GhostMaterial;

	/** Souls already home. Persisted through SaveRoll/LoadRoll (FHexRoll.Restored), so
	 *  a roll file is the complete town save: destiny + healing progress. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Hex Shuffle|Restoration")
	TArray<FIntPoint> RestoredCells;

	/** Restore the next soul (deterministically-first candidate: ring-outward from the
	 *  Pit, bridges gating the far bank). The auto-heal path; the player-agency path is
	 *  RestoreCell on a candidate of the player's choosing. */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle|Restoration")
	void RestoreNext();

	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle|Restoration")
	void RestoreAll();

	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle|Restoration")
	void ResetRestoration();

	/** Settle a soul on a specific candidate cell. Returns false (with a warning) if
	 *  the cell isn't currently a legal candidate. */
	UFUNCTION(BlueprintCallable, Category = "Hex Shuffle|Restoration")
	bool RestoreCell(FIntPoint Axial);

	/** Unrestored cells a soul could settle next: adjacent to the core or to a restored
	 *  PROPAGATING cell. Land and bridges propagate; open water never does — the far
	 *  bank waits for its bridge (Docs/Rivers.md §1). If strict propagation strands
	 *  souls (a bridge-less roll), falls back to plain adjacency so all souls stay
	 *  reachable. Sorted ring-outward, then axial — deterministic. */
	UFUNCTION(BlueprintCallable, Category = "Hex Shuffle|Restoration")
	TArray<FIntPoint> GetRestorationCandidates() const;

	// --- River & banks (Rivers.md R4) -----------------------------------------------

	/** Which bank of the River a cell sits on, relative to flow (inflow → outflow):
	 *  0 = Left Bank, 1 = Right Bank (Rive Gauche / Rive Droite). Water cells, the
	 *  core, and riverless rolls return -1 — the River and the wound belong to both. */
	UFUNCTION(BlueprintCallable, Category = "Hex Shuffle|River")
	int32 GetBank(FIntPoint Axial) const;

	/** "Left Bank" / "Right Bank" / "" — the diegetic half of an address. */
	UFUNCTION(BlueprintCallable, Category = "Hex Shuffle|River")
	FString GetBankName(FIntPoint Axial) const;

	/** Filename (in Design/Rolls, .json optional) or a full path, to reload with Load Roll. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Hex Shuffle|Rolls")
	FString RollToLoad;

	/** Save the current layout to Design/Rolls/Roll_seed<N>.json (the durable record). */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle|Rolls")
	void SaveRoll();

	/** Reload the roll named by RollToLoad and rebuild it verbatim (no re-growth). */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Hex Shuffle|Rolls")
	void LoadRoll();

private:
	UPROPERTY(VisibleAnywhere, Category = "Hex Shuffle")
	TObjectPtr<USceneComponent> Root;

	UPROPERTY(VisibleAnywhere, Category = "Hex Shuffle")
	TObjectPtr<UTextRenderComponent> PopLabel;

	UPROPERTY(Transient)
	TMap<TObjectPtr<UStaticMesh>, TObjectPtr<UInstancedStaticMeshComponent>> MeshToISM;

	// Ghost twins: same meshes, GhostMaterial on every slot, no collision.
	UPROPERTY(Transient)
	TMap<TObjectPtr<UStaticMesh>, TObjectPtr<UInstancedStaticMeshComponent>> MeshToGhostISM;

	// Calibration cache: each tile's true ROAD and WATER masks (edges each layer's
	// geometry reaches), at yaw 0. Layers measured independently from material sections.
	UPROPERTY(Transient)
	TArray<int32> TileRealMask;

	UPROPERTY(Transient)
	TArray<int32> TileRealWaterMask;
	bool bCalibrated = false;

	// The last network Build() placed — what SaveRoll writes out and what Python's
	// roll diagnostics read (including after a LoadRoll, which sets LastNetwork from
	// JSON and isn't reproducible by re-growing). AllowPrivateAccess opts past UE's
	// "no BP on private members" rule — the field stays C++-private but
	// reflection/BP/Python can read it.
	UPROPERTY(Transient, BlueprintReadOnly, Category = "Hex Shuffle|Debug", meta = (AllowPrivateAccess = "true"))
	FHexNetwork LastNetwork;

	void MeasureCalibration();
	int32 MeasureTileMask(UStaticMesh* Mesh, const TCHAR* MaterialKey) const;
	bool FindPlacement(int32 CellMask, int32 CellWaterMask, int32& OutTile, int32& OutYawSteps) const;

	void Build(const FHexNetwork& Net);
	void RefreshPresentation();
	bool BuildRiverPath(TArray<FVector2D>& OutPts) const;
	UInstancedStaticMeshComponent* GetOrCreateISM(UStaticMesh* Mesh);
	UInstancedStaticMeshComponent* GetOrCreateGhostISM(UStaticMesh* Mesh);
};
