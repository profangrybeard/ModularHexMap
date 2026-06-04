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
	PopLabel->SetText(FText::FromString(TEXT("Vacancies: 0")));
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
}

void AHexShuffleGenerator::Recalibrate()
{
	bCalibrated = false;
	MeasureCalibration();
}

// Read the mesh's M_Road material section and see which of the 6 edge midpoints its
// carriageway vertices reach -> the tile's true road mask at yaw 0. CPU-only (no physics),
// and it captures any import mirror/rotation because it reads the actual geometry.
int32 AHexShuffleGenerator::MeasureTileMask(UStaticMesh* Mesh) const
{
	if (!Mesh) { return 0; }
	const FStaticMeshRenderData* RD = Mesh->GetRenderData();
	if (!RD || RD->LODResources.Num() == 0) { return 0; }
	const FStaticMeshLODResources& LOD = RD->LODResources[0];

	// Locate the road material slot.
	int32 RoadSlot = INDEX_NONE;
	const TArray<FStaticMaterial>& Mats = Mesh->GetStaticMaterials();
	for (int32 i = 0; i < Mats.Num(); ++i)
	{
		const FString SlotName = Mats[i].MaterialSlotName.ToString();
		const FString MatName = Mats[i].MaterialInterface ? Mats[i].MaterialInterface->GetName() : FString();
		if (SlotName.Contains(TEXT("Road")) || MatName.Contains(TEXT("Road")))
		{
			RoadSlot = i;
			break;
		}
	}
	if (RoadSlot == INDEX_NONE) { return 0; } // no road section -> blank tile

	const FPositionVertexBuffer& PVB = LOD.VertexBuffers.PositionVertexBuffer;
	FIndexArrayView Indices = LOD.IndexBuffer.GetArrayView();

	const float Inr = HexCircumradiusUU * 0.86602540378f;
	FVector2D EdgeMid[6];
	for (int32 e = 0; e < 6; ++e)
	{
		const float A = FMath::DegreesToRadians(HexGrid::EdgeAngleDeg(e));
		EdgeMid[e] = FVector2D(Inr * FMath::Cos(A), Inr * FMath::Sin(A));
	}
	const float NearDist = HexCircumradiusUU * 0.30f;

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
	int32 PopMismatches = 0;

	for (int32 i = 0; i < N; ++i)
	{
		UStaticMesh* M = TileSet->Tiles[i].Mesh.LoadSynchronous();
		const int32 Measured = MeasureTileMask(M);
		TileRealMask[i] = Measured;

		const int32 Authored = UHexTileSet::TileMask(TileSet->Tiles[i]);
		const int32 PM = PopCount6(Measured);
		const int32 PA = PopCount6(Authored);
		if (PM != PA) { ++PopMismatches; }

		UE_LOG(LogTemp, Display, TEXT("HexShuffle tile '%s': measured=0x%02X(%d) authored=0x%02X(%d) %s"),
			*TileSet->Tiles[i].Name.ToString(), Measured, PM, Authored, PA, (PM == PA ? TEXT("OK") : TEXT("MISMATCH")));
	}

	// Road-count is rotation-invariant, so every measured popcount must equal the authored one.
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

bool AHexShuffleGenerator::FindPlacement(int32 CellMask, int32& OutTile, int32& OutYawSteps) const
{
	for (int32 i = 0; i < TileRealMask.Num(); ++i)
	{
		for (int32 k = 0; k < 6; ++k)
		{
			// World mask of this tile placed at yaw 60*k is RotateLeft(real, k) for UE's
			// yaw convention; bInvertYawShift flips it if turns come out mirrored.
			const int32 Rot = bInvertYawShift ? ((6 - k) % 6) : k;
			if (HexGrid::RotateMask6(TileRealMask[i], Rot) == CellMask)
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

void AHexShuffleGenerator::Randomize()
{
	++Seed;
	if (!TileSet)
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: no TileSet assigned."));
		return;
	}
	if (bAutoCalibrate && !bCalibrated)
	{
		MeasureCalibration();
	}
	// Placeholder fixed core (Pit + ring 1) until the authored core-layout asset exists; the
	// frontier grows around it. Swap MakePlaceholderCore for the authored cells when ready.
	const TArray<FHexCellResult> Core = UHexMapGrowthLibrary::MakePlaceholderCore(Growth);
	const FHexNetwork Net = UHexMapGrowthLibrary::GrowRoadNetwork(Growth, Core, Seed);
	Build(Net);
}

void AHexShuffleGenerator::Build(const FHexNetwork& Net)
{
	Clear();
	LastNetwork = Net; // remember what we placed, so SaveRoll can write it out

	const bool bUseMeasured = bCalibrated && TileRealMask.Num() == TileSet->Tiles.Num();
	int32 Unresolved = 0;
	int32 Vacancies = 0;

	for (const FHexCellResult& Cell : Net.Cells)
	{
		int32 TileIdx = INDEX_NONE;
		int32 YawSteps = 0;

		const bool bFound = bUseMeasured
			? FindPlacement(Cell.RoadMask, TileIdx, YawSteps)
			: TileSet->FindTileForMask(Cell.RoadMask, TileIdx, YawSteps);

		if (!bFound) { ++Unresolved; continue; }

		UStaticMesh* Mesh = TileSet->Tiles[TileIdx].Mesh.LoadSynchronous();
		if (!Mesh) { ++Unresolved; continue; }

		// The fixed core (Pit + story ring) follows a narrative restoration arc, not population,
		// so it's excluded from the rescue-capacity tally — only frontier tiles count.
		if (HexGrid::Distance(Cell.Axial) > Growth.CoreRadius)
		{
			Vacancies += TileSet->Tiles[TileIdx].Occupancy;
		}

		UInstancedStaticMeshComponent* ISM = GetOrCreateISM(Mesh);
		if (!ISM) { continue; }

		const FVector2D XY = HexGrid::WorldXY(Cell.Axial, HexCircumradiusUU);
		FTransform X;
		X.SetLocation(FVector(XY.X, XY.Y, 0.f));
		X.SetRotation(FQuat(FRotator(0.f, ExtraYawDeg + 60.f * YawSteps, 0.f)));
		ISM->AddInstance(X, /*bWorldSpace=*/false);
	}

	EstimatedVacancies = Vacancies;
	if (PopLabel)
	{
		PopLabel->SetText(FText::FromString(FString::Printf(TEXT("Vacancies: %d"), Vacancies)));
	}

	UE_LOG(LogTemp, Display, TEXT("HexShuffle: built %d cells (%s resolver), %d unresolved, vacancies=%d."),
		Net.Cells.Num(), bUseMeasured ? TEXT("measured") : TEXT("authored"), Unresolved, Vacancies);
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
	Roll.Vacancies = EstimatedVacancies;
	Roll.Growth = Growth;
	Roll.Network = LastNetwork;

	FString Json;
	if (!FJsonObjectConverter::UStructToJsonObjectString(Roll, Json))
	{
		UE_LOG(LogTemp, Warning, TEXT("HexShuffle: failed to serialize roll."));
		return;
	}

	const FString Dir = RollsDir();
	IFileManager::Get().MakeDirectory(*Dir, /*Tree=*/true);
	const FString File = Dir / FString::Printf(TEXT("Roll_seed%d_vac%d.json"), Seed, EstimatedVacancies);

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

	// Restore provenance, then rebuild the saved network verbatim (no re-growth).
	Seed = Roll.Seed;
	Growth = Roll.Growth;
	Build(Roll.Network);

	UE_LOG(LogTemp, Display, TEXT("HexShuffle: loaded roll '%s' (seed %d, %d cells)."),
		*Path, Roll.Seed, Roll.Network.Cells.Num());
}
