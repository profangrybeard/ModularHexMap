// Copyright (c) 2026. All rights reserved.

#include "HexShuffleGenerator.h"
#include "HexTileSet.h"
#include "HexCoordinates.h"
#include "Components/InstancedStaticMeshComponent.h"
#include "Components/TextRenderComponent.h"
#include "Engine/StaticMesh.h"
#include "StaticMeshResources.h"
#include "Materials/MaterialInterface.h"
#include "JsonObjectConverter.h"
#include "Algo/Reverse.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "HAL/FileManager.h"

AHexShuffleGenerator::AHexShuffleGenerator()
{
	PrimaryActorTick.bCanEverTick = false;
	Root = CreateDefaultSubobject<USceneComponent>(TEXT("Root"));
	SetRootComponent(Root);

	PopLabel = CreateDefaultSubobject<UTextRenderComponent>(TEXT("PopLabel"));
	PopLabel->SetupAttachment(Root);
	PopLabel->SetRelativeLocation(FVector(0.f, 0.f, 400.f));
	PopLabel->SetRelativeRotation(FRotator(90.f, 0.f, 0.f)); // lie flat, readable top-down
	PopLabel->SetHorizontalAlignment(EHTA_Center);
	PopLabel->SetVerticalAlignment(EVRTA_TextCenter);
	PopLabel->SetWorldSize(150.f);
	PopLabel->SetTextRenderColor(FColor(255, 220, 80));
	PopLabel->SetText(FText::FromString(TEXT("Souls: 0")));
}

static int32 PopCount6(int32 M)
{
	int32 N = 0;
	for (int32 b = 0; b < 6; ++b) { if (M & (1 << b)) ++N; }
	return N;
}

void AHexShuffleGenerator::Clear()
{
	TArray<UInstancedStaticMeshComponent*> Existing;
	GetComponents<UInstancedStaticMeshComponent>(Existing);
	for (UInstancedStaticMeshComponent* C : Existing)
	{
		if (C) { C->DestroyComponent(); }
	}
	MeshToISM.Empty();
	MeshToGhostISM.Empty();
}

void AHexShuffleGenerator::Recalibrate()
{
	bCalibrated = false;
	MeasureCalibration();
}

// Read the mesh's keyed material section ("Road" or "Water") and see which of the 6
// edge midpoints that layer's vertices reach -> the tile's true layer mask at yaw 0.
// CPU-only (no physics), and it captures any import mirror/rotation because it reads
// the actual geometry. One measurer, two layers — the layered-mask contract.
int32 AHexShuffleGenerator::MeasureTileMask(UStaticMesh* Mesh, const TCHAR* MaterialKey) const
{
	if (!Mesh) { return 0; }
	const FStaticMeshRenderData* RD = Mesh->GetRenderData();
	if (!RD || RD->LODResources.Num() == 0) { return 0; }
	const FStaticMeshLODResources& LOD = RD->LODResources[0];

	// Locate the keyed material slot.
	int32 RoadSlot = INDEX_NONE;
	const TArray<FStaticMaterial>& Mats = Mesh->GetStaticMaterials();
	for (int32 i = 0; i < Mats.Num(); ++i)
	{
		const FString SlotName = Mats[i].MaterialSlotName.ToString();
		const FString MatName = Mats[i].MaterialInterface ? Mats[i].MaterialInterface->GetName() : FString();
		if (SlotName.Contains(MaterialKey) || MatName.Contains(MaterialKey))
		{
			RoadSlot = i;
			break;
		}
	}
	if (RoadSlot == INDEX_NONE) { return 0; } // no such section -> layer absent on this tile

	const FPositionVertexBuffer& PVB = LOD.VertexBuffers.PositionVertexBuffer;
	FIndexArrayView Indices = LOD.IndexBuffer.GetArrayView();

	const float Inr = HexCircumradiusUU * 0.86602540378f;
	FVector2D EdgeMid[6];
	for (int32 e = 0; e < 6; ++e)
	{
		const float A = FMath::DegreesToRadians(HexGrid::EdgeAngleDeg(e));
		EdgeMid[e] = FVector2D(Inr * FMath::Cos(A), Inr * FMath::Sin(A));
	}
	// ABSOLUTE tolerance (uu), not a fraction of R: the street cross-section is absolute
	// (carriageway half-width = 1.5 m = 150 uu), so the carriageway's edge-row vertices sit
	// exactly 150 uu from the midpoint. 250 gives float/tessellation slack while staying far
	// below any non-connected road geometry (the junction hub edge is ~640 uu from a midpoint).
	const float NearDist = 250.f;

	int32 Mask = 0;
	for (const FStaticMeshSection& Sec : LOD.Sections)
	{
		if (Sec.MaterialIndex != RoadSlot) { continue; }
		const uint32 End = Sec.FirstIndex + Sec.NumTriangles * 3;
		for (uint32 ii = Sec.FirstIndex; ii < End; ++ii)
		{
			const uint32 VI = Indices[ii];
			if (VI >= PVB.GetNumVertices()) { continue; }
			const FVector3f P = PVB.VertexPosition(VI);
			const FVector2D XY((float)P.X, (float)P.Y);
			for (int32 e = 0; e < 6; ++e)
			{
				if ((Mask & (1 << e)) == 0 && FVector2D::Distance(XY, EdgeMid[e]) < NearDist)
				{
					Mask |= (1 << e);
				}
			}
		}
	}
	return Mask;
}

void AHexShuffleGenerator::MeasureCalibration()
{
	bCalibrated = false;
	if (!TileSet) { return; }

	const int32 N = TileSet->Tiles.Num();
	TileRealMask.Init(0, N);
	TileRealWaterMask.Init(0, N);
	int32 PopMismatches = 0;

	for (int32 i = 0; i < N; ++i)
	{
		UStaticMesh* M = TileSet->Tiles[i].Mesh.LoadSynchronous();
		const int32 Measured = MeasureTileMask(M, TEXT("Road"));
		const int32 MeasuredW = MeasureTileMask(M, TEXT("Water"));
		TileRealMask[i] = Measured;
		TileRealWaterMask[i] = MeasuredW;

		const int32 Authored = UHexTileSet::TileMask(TileSet->Tiles[i]);
		const int32 AuthoredW = TileSet->Tiles[i].WaterMask & 0x3F;
		const int32 PM = PopCount6(Measured), PA = PopCount6(Authored);
		const int32 PMW = PopCount6(MeasuredW), PAW = PopCount6(AuthoredW);
		if (PM != PA || PMW != PAW) { ++PopMismatches; }

		UE_LOG(LogTemp, Display, TEXT("HexShuffle tile '%s': road measured=0x%02X(%d) authored=0x%02X(%d) | water measured=0x%02X(%d) authored=0x%02X(%d) %s"),
			*TileSet->Tiles[i].Name.ToString(), Measured, PM, Authored, PA, MeasuredW, PMW, AuthoredW, PAW,
			((PM == PA && PMW == PAW) ? TEXT("OK") : TEXT("MISMATCH")));
	}

	// Edge-count is rotation-invariant, so every measured popcount must equal the
	// authored one — per layer.
	bCalibrated = (PopMismatches == 0);

	if (bCalibrated)
	{
		UE_LOG(LogTemp, Display, TEXT("HexShuffle: calibration OK (%d tiles measured from geometry)."), N);
	}
	else
	{
		UE_LOG(LogTemp, Warning,
			TEXT("HexShuffle: calibration distrusted (%d pop-mismatches) -> falling back to authored sockets."),
			PopMismatches);
	}
}

bool AHexShuffleGenerator::FindPlacement(int32 CellMask, int32 CellWaterMask, int32& OutTile, int32& OutYawSteps) const
{
	for (int32 i = 0; i < TileRealMask.Num(); ++i)
	{
		for (int32 k = 0; k < 6; ++k)
		{
			// World mask of this tile placed at yaw 60*k is RotateLeft(real, k) for UE's
			// yaw convention; bInvertYawShift flips it if turns come out mirrored. BOTH
			// layers must match under the SAME rotation (the layered-mask contract).
			const int32 Rot = bInvertYawShift ? ((6 - k) % 6) : k;
			if (HexGrid::RotateMask6(TileRealMask[i], Rot) == CellMask &&
				HexGrid::RotateMask6(TileRealWaterMask[i], Rot) == CellWaterMask)
			{
				OutTile = i;
				OutYawSteps = k;
				return true;
			}
		}
	}
	OutTile = INDEX_NONE;
	OutYawSteps = 0;
	return false;
}

UInstancedStaticMeshComponent* AHexShuffleGenerator::GetOrCreateISM(UStaticMesh* Mesh)
{
	if (!Mesh) { return nullptr; }
	if (TObjectPtr<UInstancedStaticMeshComponent>* Found = MeshToISM.Find(Mesh))
	{
		return *Found;
	}
	UInstancedStaticMeshComponent* ISM = NewObject<UInstancedStaticMeshComponent>(this);
	ISM->SetMobility(EComponentMobility::Movable);
	ISM->SetStaticMesh(Mesh);
	ISM->SetupAttachment(Root);
	ISM->RegisterComponent();
	MeshToISM.Add(Mesh, ISM);
	return ISM;
}

// Ghost twin of GetOrCreateISM: GhostMaterial on every slot, no collision — the
// destiny silhouette you can see but not stand on.
UInstancedStaticMeshComponent* AHexShuffleGenerator::GetOrCreateGhostISM(UStaticMesh* Mesh)
{
	if (!Mesh) { return nullptr; }
	if (TObjectPtr<UInstancedStaticMeshComponent>* Found = MeshToGhostISM.Find(Mesh))
	{
		return *Found;
	}
	UInstancedStaticMeshComponent* ISM = NewObject<UInstancedStaticMeshComponent>(this);
	ISM->SetMobility(EComponentMobility::Movable);
	ISM->SetStaticMesh(Mesh);
	ISM->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	if (GhostMaterial)
	{
		for (int32 i = 0; i < Mesh->GetStaticMaterials().Num(); ++i)
		{
			ISM->SetMaterial(i, GhostMaterial);
		}
	}
	ISM->SetupAttachment(Root);
	ISM->RegisterComponent();
	MeshToGhostISM.Add(Mesh, ISM);
	return ISM;
}

void AHexShuffleGenerator::Randomize()
{
	// The reroll button: advance to the next seed and build it. Tools that need a
	// SPECIFIC seed placed (constrained randomize) call BuildFromSeed directly.
	BuildFromSeed(Seed + 1);
}

void AHexShuffleGenerator::BuildFromSeed(int32 InSeed)
{
	Seed = InSeed;
	RestoredCells.Reset();   // a fresh destiny starts at Pop 1 (you)
	if (!TileSet)
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: no TileSet assigned."));
		return;
	}
	if (bAutoCalibrate && !bCalibrated)
	{
		MeasureCalibration();
	}
	// Pinned core: the authored layout (bespoke Pit-core tiles) if assigned, else the placeholder.
	TArray<FHexCellResult> Core;
	if (CoreLayout && CoreLayout->Cells.Num() > 0)
	{
		for (const FHexCoreCell& CC : CoreLayout->Cells)
		{
			FHexCellResult R;
			R.Axial = CC.Axial;
			R.RoadMask = CC.RoadMask;
			Core.Add(R);
		}
	}
	else
	{
		Core = UHexMapGrowthLibrary::MakePlaceholderCore(Growth);
	}
	const FHexNetwork Net = UHexMapGrowthLibrary::GrowRoadNetwork(Growth, Core, Seed);
	Build(Net);
}

void AHexShuffleGenerator::Build(const FHexNetwork& Net)
{
	Clear();
	LastNetwork = Net; // remember what we placed, so SaveRoll / diagnostics read the truth

	const bool bUseMeasured = bCalibrated
		&& TileRealMask.Num() == TileSet->Tiles.Num()
		&& TileRealWaterMask.Num() == TileSet->Tiles.Num();
	int32 Unresolved = 0;
	int32 SoulCount = 0;
	int32 CorePlaced = 0;

	// Hardwired core: map each pinned axial to its bespoke mesh (placed verbatim at yaw 0,
	// resolver bypassed). The frontier grows around it and connects to its exposed road stubs.
	TMap<FIntPoint, TPair<UStaticMesh*, int32>> CoreMesh;
	if (CoreLayout)
	{
		for (const FHexCoreCell& CC : CoreLayout->Cells)
		{
			if (UStaticMesh* M = CC.Mesh.LoadSynchronous())
			{
				CoreMesh.Add(CC.Axial, TPair<UStaticMesh*, int32>(M, CC.RoadMask));
			}
		}
	}

	// Restoration: in restoration mode, frontier cells not yet restored render as the
	// ghost silhouette (street mesh only, GhostMaterial, no collision) — the destiny's
	// empty shelves. The core scar is always solid.
	TSet<FIntPoint> RestoredSet(RestoredCells);

	for (const FHexCellResult& Cell : Net.Cells)
	{
		const FVector2D XY = HexGrid::WorldXY(Cell.Axial, HexCircumradiusUU);

		// 1 frontier tile = 1 soul (the Pop One spine); the core is the scar, never counted.
		if (HexGrid::Distance(Cell.Axial) > Growth.CoreRadius) { ++SoulCount; }

		const bool bGhost = bRestorationMode
			&& HexGrid::Distance(Cell.Axial) > Growth.CoreRadius
			&& !RestoredSet.Contains(Cell.Axial);

		// Core cell: drop the bespoke mesh verbatim, skip the resolver (the core follows a
		// narrative restoration arc, not the soul count).
		if (const TPair<UStaticMesh*, int32>* CoreE = CoreMesh.Find(Cell.Axial))
		{
			if (UInstancedStaticMeshComponent* ISM = GetOrCreateISM(CoreE->Key))
			{
				// Correct for glTF import re-orientation (the importer mirrors+rotates the mesh):
				// measure the mesh's real road mask and rotate it onto the AUTHORED mask, exactly
				// as the frontier resolver does. Without this the core places at a fixed yaw and
				// comes out mis-rotated (rings off the mirror axis are visibly wrong every roll).
				int32 CoreYaw = 0;
				const int32 Real = MeasureTileMask(CoreE->Key, TEXT("Road"));
				for (int32 k = 0; k < 6; ++k)
				{
					const int32 Rot = bInvertYawShift ? ((6 - k) % 6) : k;
					if (HexGrid::RotateMask6(Real, Rot) == CoreE->Value) { CoreYaw = k; break; }
				}
				FTransform X;
				X.SetLocation(FVector(XY.X, XY.Y, 0.f));
				X.SetRotation(FQuat(FRotator(0.f, ExtraYawDeg + 60.f * CoreYaw, 0.f)));
				ISM->AddInstance(X, /*bWorldSpace=*/false);
				++CorePlaced;
			}
			continue;
		}

		// Frontier cell: resolve the grown masks (both layers) to a tile + rotation.
		int32 TileIdx = INDEX_NONE;
		int32 YawSteps = 0;
		const bool bFound = bUseMeasured
			? FindPlacement(Cell.RoadMask, Cell.WaterMask, TileIdx, YawSteps)
			: TileSet->FindTileForMask(Cell.RoadMask, Cell.WaterMask, TileIdx, YawSteps);

		if (!bFound) { ++Unresolved; continue; }

		UStaticMesh* Mesh = TileSet->Tiles[TileIdx].Mesh.LoadSynchronous();
		if (!Mesh) { ++Unresolved; continue; }

		FTransform X;
		X.SetLocation(FVector(XY.X, XY.Y, 0.f));
		X.SetRotation(FQuat(FRotator(0.f, ExtraYawDeg + 60.f * YawSteps, 0.f)));

		if (bGhost)
		{
			// Unrestored: the street/lot silhouette only. The building (and its soul)
			// arrives with restoration.
			if (UInstancedStaticMeshComponent* GISM = GetOrCreateGhostISM(Mesh))
			{
				GISM->AddInstance(X, /*bWorldSpace=*/false);
			}
			continue;
		}

		UInstancedStaticMeshComponent* ISM = GetOrCreateISM(Mesh);
		if (!ISM) { continue; }
		ISM->AddInstance(X, /*bWorldSpace=*/false);

		// Building overlay: same world transform as the street tile (the facade line is
		// the road centerline offset by KEEP_HW, so the same yaw aligns the facades).
		// Parallel ISM keyed on the building mesh -> distinct from the street ISM.
		if (UStaticMesh* BMesh = TileSet->Tiles[TileIdx].BuildingMesh.LoadSynchronous())
		{
			if (UInstancedStaticMeshComponent* BISM = GetOrCreateISM(BMesh))
			{
				BISM->AddInstance(X, /*bWorldSpace=*/false);
			}
		}
	}

	Souls = SoulCount;
	if (PopLabel)
	{
		PopLabel->SetText(FText::FromString(bRestorationMode
			? FString::Printf(TEXT("Pop %d / %d"), RestoredCells.Num() + 1, SoulCount + 1)
			: FString::Printf(TEXT("Souls: %d"), SoulCount)));
	}

	UE_LOG(LogTemp, Display, TEXT("HexShuffle: built %d cells (%s resolver), core=%d, %d unresolved, souls=%d, restored=%d%s."),
		Net.Cells.Num(), bUseMeasured ? TEXT("measured") : TEXT("authored"), CorePlaced, Unresolved, SoulCount,
		RestoredCells.Num(), bRestorationMode ? TEXT(" [restoration]") : TEXT(""));
}

void AHexShuffleGenerator::RefreshPresentation()
{
	if (LastNetwork.Cells.Num() == 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: no network yet — Randomize (or Load Roll) first."));
		return;
	}
	// Build() assigns LastNetwork = Net; rebuilding from our own member needs a copy
	// (self-assignment of the array is what we'd otherwise hand it).
	const FHexNetwork Copy = LastNetwork;
	Build(Copy);
}

TArray<FIntPoint> AHexShuffleGenerator::GetRestorationCandidates() const
{
	TArray<FIntPoint> Out;
	if (LastNetwork.Cells.Num() == 0) { return Out; }

	TMap<FIntPoint, const FHexCellResult*> CellOf;
	for (const FHexCellResult& C : LastNetwork.Cells) { CellOf.Add(C.Axial, &C); }
	const TSet<FIntPoint> Restored(RestoredCells);

	auto IsCore = [&](const FIntPoint& A) { return HexGrid::Distance(A) <= Growth.CoreRadius; };
	// A neighbor spreads the healing if it's the core (the wound seeds it) or a
	// restored cell that isn't open water — bridges (road over water) propagate,
	// the bare river never does, so the far bank waits for its bridge.
	auto Propagates = [&](const FIntPoint& A) -> bool
	{
		if (IsCore(A)) { return true; }
		if (!Restored.Contains(A)) { return false; }
		const FHexCellResult* C = CellOf.FindRef(A);
		return C && !(C->WaterMask != 0 && C->RoadMask == 0);
	};

	for (const FHexCellResult& C : LastNetwork.Cells)
	{
		if (IsCore(C.Axial) || Restored.Contains(C.Axial)) { continue; }
		for (int32 e = 0; e < 6; ++e)
		{
			if (Propagates(HexGrid::Neighbor(C.Axial, e))) { Out.Add(C.Axial); break; }
		}
	}

	if (Out.Num() == 0)
	{
		// Strict propagation stranded souls (a bridge-less far bank). Relax to plain
		// adjacency so all 120 stay reachable — the river itself carries the healing.
		for (const FHexCellResult& C : LastNetwork.Cells)
		{
			if (IsCore(C.Axial) || Restored.Contains(C.Axial)) { continue; }
			for (int32 e = 0; e < 6; ++e)
			{
				const FIntPoint N = HexGrid::Neighbor(C.Axial, e);
				if (IsCore(N) || Restored.Contains(N)) { Out.Add(C.Axial); break; }
			}
		}
		if (Out.Num() > 0)
		{
			UE_LOG(LogTemp, Display, TEXT("HexShuffle: restoration crossed open water (no bridge on this destiny)."));
		}
	}

	Out.Sort([](const FIntPoint& A, const FIntPoint& B)
	{
		const int32 DA = HexGrid::Distance(A), DB = HexGrid::Distance(B);
		if (DA != DB) { return DA < DB; }
		return (A.X != B.X) ? (A.X < B.X) : (A.Y < B.Y);
	});
	return Out;
}

void AHexShuffleGenerator::RestoreNext()
{
	const TArray<FIntPoint> Candidates = GetRestorationCandidates();
	if (Candidates.Num() == 0)
	{
		UE_LOG(LogTemp, Display, TEXT("HexShuffle: every soul is home (or no roll yet)."));
		return;
	}
	RestoredCells.Add(Candidates[0]);
	RefreshPresentation();
}

bool AHexShuffleGenerator::RestoreCell(FIntPoint Axial)
{
	if (!GetRestorationCandidates().Contains(Axial))
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: (%d,%d) is not a restoration candidate."), Axial.X, Axial.Y);
		return false;
	}
	RestoredCells.Add(Axial);
	RefreshPresentation();
	return true;
}

void AHexShuffleGenerator::RestoreAll()
{
	int32 Guard = 100000;
	while (--Guard > 0)
	{
		const TArray<FIntPoint> Candidates = GetRestorationCandidates();
		if (Candidates.Num() == 0) { break; }
		RestoredCells.Add(Candidates[0]);
	}
	RefreshPresentation();
}

void AHexShuffleGenerator::ResetRestoration()
{
	RestoredCells.Reset();
	RefreshPresentation();
}

// Ordered river centerline (cell centers, inflow -> outflow) from the placed network.
// Walks the water path graph from a boundary endpoint, then orients by the core gates:
// the OUTFLOW gate Y is the ring-1 water cell whose CCW-rotated axial equals the other
// gate X (the injection contract: X sits CCW-next from Y).
bool AHexShuffleGenerator::BuildRiverPath(TArray<FVector2D>& OutPts) const
{
	OutPts.Reset();
	if (LastNetwork.Cells.Num() == 0) { return false; }

	TMap<FIntPoint, int32> WaterOf;
	for (const FHexCellResult& C : LastNetwork.Cells)
	{
		if (C.WaterMask != 0) { WaterOf.Add(C.Axial, C.WaterMask); }
	}
	if (WaterOf.Num() < 2) { return false; }

	// Endpoints: water cells with a bit pointing off the placed region.
	TArray<FIntPoint> Ends;
	for (const TPair<FIntPoint, int32>& W : WaterOf)
	{
		for (int32 e = 0; e < 6; ++e)
		{
			if ((W.Value & (1 << e)) && !WaterOf.Contains(HexGrid::Neighbor(W.Key, e)))
			{
				const FIntPoint N = HexGrid::Neighbor(W.Key, e);
				bool bInRegion = false;
				for (const FHexCellResult& C : LastNetwork.Cells)
				{
					if (C.Axial == N) { bInRegion = true; break; }
				}
				if (!bInRegion) { Ends.AddUnique(W.Key); }
			}
		}
	}
	if (Ends.Num() == 0) { return false; }

	// Walk from one endpoint along mutual water edges.
	TArray<FIntPoint> Path;
	{
		FIntPoint Cur = Ends[0];
		FIntPoint Prev(MAX_int32, MAX_int32);
		int32 Guard = WaterOf.Num() + 4;
		while (--Guard > 0)
		{
			Path.Add(Cur);
			FIntPoint Next = Prev;
			bool bFound = false;
			const int32 M = WaterOf[Cur];
			for (int32 e = 0; e < 6; ++e)
			{
				if ((M & (1 << e)) == 0) { continue; }
				const FIntPoint N = HexGrid::Neighbor(Cur, e);
				if (N == Prev || !WaterOf.Contains(N)) { continue; }
				if ((WaterOf[N] & (1 << ((e + 3) % 6))) == 0) { continue; }
				Next = N; bFound = true; break;
			}
			if (!bFound) { break; }
			Prev = Cur; Cur = Next;
		}
	}
	if (Path.Num() < 2) { return false; }

	// Orient inflow -> outflow: find the two ring-1 gates; Y(outflow) satisfies
	// rotateCCW(Y) == X. If the walk visits Y before X, we started at the outflow
	// end — reverse.
	FIntPoint GateA(MAX_int32, 0), GateB(MAX_int32, 0);
	for (const TPair<FIntPoint, int32>& W : WaterOf)
	{
		if (HexGrid::Distance(W.Key) <= Growth.CoreRadius)
		{
			if (GateA.X == MAX_int32) { GateA = W.Key; }
			else { GateB = W.Key; }
		}
	}
	if (GateB.X != MAX_int32)
	{
		auto RotCCW = [](const FIntPoint& A) { return FIntPoint(-A.Y, A.X + A.Y); };
		const FIntPoint Y = (RotCCW(GateA) == GateB) ? GateA
		                  : (RotCCW(GateB) == GateA) ? GateB : GateA;
		const int32 IdxY = Path.IndexOfByKey(Y);
		const FIntPoint X = (Y == GateA) ? GateB : GateA;
		const int32 IdxX = Path.IndexOfByKey(X);
		if (IdxY != INDEX_NONE && IdxX != INDEX_NONE && IdxY < IdxX)
		{
			Algo::Reverse(Path);
		}
	}

	for (const FIntPoint& C : Path)
	{
		OutPts.Add(HexGrid::WorldXY(C, HexCircumradiusUU));
	}
	return true;
}

int32 AHexShuffleGenerator::GetBank(FIntPoint Axial) const
{
	if (HexGrid::Distance(Axial) <= Growth.CoreRadius) { return -1; }   // the wound is both banks
	for (const FHexCellResult& C : LastNetwork.Cells)
	{
		if (C.Axial == Axial && C.WaterMask != 0) { return -1; }        // the River is the River
	}
	TArray<FVector2D> Pts;
	if (!BuildRiverPath(Pts)) { return -1; }

	const FVector2D P = HexGrid::WorldXY(Axial, HexCircumradiusUU);
	float BestD2 = MAX_flt;
	float BestCross = 0.f;
	for (int32 i = 0; i + 1 < Pts.Num(); ++i)
	{
		const FVector2D A = Pts[i], B = Pts[i + 1];
		const FVector2D AB = B - A;
		const float L2 = AB.SizeSquared();
		const float T = (L2 > 0.f) ? FMath::Clamp(FVector2D::DotProduct(P - A, AB) / L2, 0.f, 1.f) : 0.f;
		const FVector2D Q = A + AB * T;
		const float D2 = (P - Q).SizeSquared();
		if (D2 < BestD2)
		{
			BestD2 = D2;
			BestCross = AB.X * (P.Y - A.Y) - AB.Y * (P.X - A.X);
		}
	}
	return (BestCross > 0.f) ? 0 : 1;   // left of flow = Left Bank
}

FString AHexShuffleGenerator::GetBankName(FIntPoint Axial) const
{
	switch (GetBank(Axial))
	{
	case 0:  return TEXT("Left Bank");
	case 1:  return TEXT("Right Bank");
	default: return FString();
	}
}

static FString RollsDir()
{
	return FPaths::ConvertRelativePathToFull(FPaths::ProjectDir() / TEXT("Design") / TEXT("Rolls"));
}

void AHexShuffleGenerator::SaveRoll()
{
	if (LastNetwork.Cells.Num() == 0)
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: nothing to save — Randomize (or Load) a roll first."));
		return;
	}

	FHexRoll Roll;
	Roll.Seed = Seed;
	Roll.Growth = Growth;
	Roll.Network = LastNetwork;
	Roll.Restored = RestoredCells;   // destiny + healing progress = the complete save

	FString Json;
	if (!FJsonObjectConverter::UStructToJsonObjectString(Roll, Json))
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: failed to serialize roll."));
		return;
	}

	const FString Dir = RollsDir();
	IFileManager::Get().MakeDirectory(*Dir, /*Tree=*/true);
	const FString File = Dir / FString::Printf(TEXT("Roll_seed%d.json"), Seed);

	if (FFileHelper::SaveStringToFile(Json, *File))
	{
		UE_LOG(LogTemp, Display, TEXT("HexShuffle: saved roll -> %s"), *File);
	}
	else
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: failed to write %s"), *File);
	}
}

void AHexShuffleGenerator::LoadRoll()
{
	if (RollToLoad.IsEmpty())
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: set RollToLoad to a filename in Design/Rolls (or a full path)."));
		return;
	}

	// Accept a bare filename (resolved under Design/Rolls, .json appended) or a full path.
	FString Path = RollToLoad;
	if (FPaths::GetPath(Path).IsEmpty())
	{
		if (!Path.EndsWith(TEXT(".json"))) { Path += TEXT(".json"); }
		Path = RollsDir() / Path;
	}

	FString Json;
	if (!FFileHelper::LoadFileToString(Json, *Path))
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: cannot read roll '%s'."), *Path);
		return;
	}

	FHexRoll Roll;
	if (!FJsonObjectConverter::JsonObjectStringToUStruct(Json, &Roll, /*CheckFlags=*/0, /*SkipFlags=*/0))
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: failed to parse roll '%s'."), *Path);
		return;
	}

	if (!TileSet)
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: no TileSet assigned — cannot rebuild roll."));
		return;
	}
	if (bAutoCalibrate && !bCalibrated)
	{
		MeasureCalibration();
	}

	// Restore provenance + healing progress, then rebuild the saved network verbatim
	// (no re-growth). Old rolls lack Restored and load as a fresh Pop 1.
	Seed = Roll.Seed;
	Growth = Roll.Growth;
	RestoredCells = Roll.Restored;
	Build(Roll.Network);

	UE_LOG(LogTemp, Display, TEXT("HexShuffle: loaded roll '%s' (seed %d, %d cells)."),
		*Path, Roll.Seed, Roll.Network.Cells.Num());
}
