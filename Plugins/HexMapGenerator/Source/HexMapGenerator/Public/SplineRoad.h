// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Components/SplineMeshComponent.h"   // ESplineMeshAxis
#include "SplineRoad.generated.h"

class USplineComponent;
class UStaticMesh;

/**
 * A curved street: a USplineComponent you shape in the editor, with one
 * USplineMeshComponent per segment extruding the London cross-section
 * (SM_RoadSeg: 3 m carriageway + 1 m raised walks + curb) smoothly along it.
 *
 * This is the spline RENDER layer (proving the curve). The eventual generator
 * will build the spline points from the resolved hex road graph (corners
 * filleted into curves); for now drop one in a level, assign RoadSegmentMesh,
 * and drag the spline points.
 */
UCLASS()
class HEXMAPGENERATOR_API ASplineRoad : public AActor
{
	GENERATED_BODY()

public:
	ASplineRoad();

	virtual void OnConstruction(const FTransform& Transform) override;

	/** The editable centreline. Shape it in the viewport (Alt-drag to add points). */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Spline Road")
	TObjectPtr<USplineComponent> Spline;

	/** The cross-section piece extruded along the spline (assign SM_RoadSeg). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Road")
	TObjectPtr<UStaticMesh> RoadSegmentMesh;

	/** Forward axis of the cross-section mesh (SM_RoadSeg is modelled along +X). */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Road")
	TEnumAsByte<ESplineMeshAxis::Type> ForwardAxis = ESplineMeshAxis::X;

	/**
	 * Length (uu) of each tiled piece along the spline. 0 = use the segment mesh's own
	 * length along the forward axis (its long edge). Pieces are tiled by ARC LENGTH, so
	 * spacing stays even regardless of how far apart the spline points are. Keep points
	 * at least ~2 pieces apart (no pinches tighter than that).
	 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Spline Road", meta = (ClampMin = "0.0"))
	float PieceLength = 0.f;

	/** Rebuild the spline meshes (CallInEditor for quick manual refresh). */
	UFUNCTION(CallInEditor, BlueprintCallable, Category = "Spline Road")
	void Rebuild();

private:
	UPROPERTY(Transient)
	TArray<TObjectPtr<USplineMeshComponent>> Segments;
};
