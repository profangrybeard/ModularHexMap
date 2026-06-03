// Copyright (c) 2026. All rights reserved.

#pragma once

#include "CoreMinimal.h"

/**
 * Cube/axial hex helpers (Catlike-style), adapted to our FLAT-TOP convention:
 * edge 0 = +Y, counter-clockwise 1..5. Axial stored as FIntPoint(Q, R); cube
 * Y = -Q - R. World placement uses the contract neighbor offsets.
 */
namespace HexGrid
{
	/** Axial neighbor offsets per edge 0..5 (Q,R). */
	static const FIntPoint AxialDir[6] = {
		FIntPoint(0, 1), FIntPoint(-1, 1), FIntPoint(-1, 0),
		FIntPoint(0, -1), FIntPoint(1, -1), FIntPoint(1, 0)
	};

	FORCEINLINE FIntPoint Neighbor(const FIntPoint& C, int32 Edge)
	{
		const FIntPoint& D = AxialDir[((Edge % 6) + 6) % 6];
		return FIntPoint(C.X + D.X, C.Y + D.Y);
	}

	/** Hex distance from origin. */
	FORCEINLINE int32 Distance(const FIntPoint& C)
	{
		const int32 x = C.X;
		const int32 z = C.Y;
		const int32 y = -x - z;
		return (FMath::Abs(x) + FMath::Abs(y) + FMath::Abs(z)) / 2;
	}

	/** Axial (Q,R) -> world XY in UE units, flat-top, edge 0 along +Y. */
	FORCEINLINE FVector2D WorldXY(const FIntPoint& C, float CircumradiusUU)
	{
		const float Inr = CircumradiusUU * 0.86602540378f; // R * sqrt(3)/2
		const FVector2D Bq(1.5f * CircumradiusUU, Inr); // axial (+1,0)
		const FVector2D Br(0.f, 2.f * Inr);             // axial (0,+1)
		return float(C.X) * Bq + float(C.Y) * Br;
	}

	/** Rotate a 6-bit edge mask left by R (bit e -> bit (e+R) mod 6). */
	FORCEINLINE int32 RotateMask6(int32 Mask, int32 R)
	{
		R = ((R % 6) + 6) % 6;
		return ((Mask << R) | (Mask >> (6 - R))) & 0x3F;
	}

	/** World direction angle (degrees) of edge e: edge 0 = +Y (90), CCW. */
	FORCEINLINE float EdgeAngleDeg(int32 Edge)
	{
		return 90.f + 60.f * float(((Edge % 6) + 6) % 6);
	}
}
