// Copyright (c) 2026. All rights reserved.

#include "SplineRoad.h"

#include "Components/SplineComponent.h"
#include "Components/SplineMeshComponent.h"
#include "Engine/StaticMesh.h"

ASplineRoad::ASplineRoad()
{
	PrimaryActorTick.bCanEverTick = false;

	Spline = CreateDefaultSubobject<USplineComponent>(TEXT("Spline"));
	RootComponent = Spline;
	Spline->SetMobility(EComponentMobility::Movable);
}

void ASplineRoad::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);
	Rebuild();
}

void ASplineRoad::Rebuild()
{
	// Clear any spline meshes from a previous build (OnConstruction re-runs on edit).
	TArray<USplineMeshComponent*> Existing;
	GetComponents(Existing);
	for (USplineMeshComponent* SM : Existing)
	{
		if (SM) { SM->DestroyComponent(); }
	}
	Segments.Reset();

	if (!RoadSegmentMesh || !Spline)
	{
		return;
	}

	// Piece length = the module's own long edge along the forward axis (override if set),
	// so pieces tile EVENLY by arc length no matter how far apart the spline points are.
	float PieceLen = PieceLength;
	if (PieceLen <= KINDA_SMALL_NUMBER)
	{
		const FVector Ext = RoadSegmentMesh->GetBoundingBox().GetSize();
		PieceLen = (ForwardAxis == ESplineMeshAxis::Y) ? Ext.Y
		         : (ForwardAxis == ESplineMeshAxis::Z) ? Ext.Z
		         : Ext.X;
	}
	if (PieceLen <= KINDA_SMALL_NUMBER)
	{
		return;
	}

	const float SplineLen = Spline->GetSplineLength();
	const int32 NumPieces = FMath::Max(1, FMath::RoundToInt(SplineLen / PieceLen));
	const float Step = SplineLen / NumPieces;
	const ESplineCoordinateSpace::Type Space = ESplineCoordinateSpace::Local;

	for (int32 i = 0; i < NumPieces; ++i)
	{
		const float D0 = i * Step;
		const float D1 = (i + 1) * Step;

		const FVector StartPos = Spline->GetLocationAtDistanceAlongSpline(D0, Space);
		const FVector EndPos   = Spline->GetLocationAtDistanceAlongSpline(D1, Space);
		// Unit tangents scaled to the piece length -> even Hermite, C1 across boundaries.
		const FVector StartTan = Spline->GetDirectionAtDistanceAlongSpline(D0, Space) * Step;
		const FVector EndTan   = Spline->GetDirectionAtDistanceAlongSpline(D1, Space) * Step;

		USplineMeshComponent* SM = NewObject<USplineMeshComponent>(this);
		SM->SetMobility(EComponentMobility::Movable);
		SM->SetupAttachment(Spline);
		SM->RegisterComponent();
		SM->SetStaticMesh(RoadSegmentMesh);
		SM->SetForwardAxis(ForwardAxis, /*bUpdateMesh=*/false);
		SM->SetStartAndEnd(StartPos, StartTan, EndPos, EndTan, /*bUpdateMesh=*/true);
		SM->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
		Segments.Add(SM);
	}
}
