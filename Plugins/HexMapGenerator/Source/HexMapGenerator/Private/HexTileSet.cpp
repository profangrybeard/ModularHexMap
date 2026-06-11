// Copyright (c) 2026. All rights reserved.

#include "HexTileSet.h"
#include "HexCoordinates.h"
#include "Math/RandomStream.h"

int32 UHexTileSet::TileMask(const FHexTileDef& Tile)
{
	int32 M = 0;
	const int32 N = FMath::Min(Tile.Edges.Num(), 6);
	for (int32 e = 0; e < N; ++e)
	{
		if (Tile.Edges[e] == EHexEdgeSocket::Road)
		{
			M |= (1 << e);
		}
	}
	return M;
}

int32 UHexTileSet::PickWeightedCandidate(TArrayView<const float> Weights, const FRandomStream* Stream)
{
	if (Weights.Num() <= 1 || !Stream)
	{
		return 0; // legacy: first match wins (also the no-entropy tool path)
	}
	float Total = 0.f;
	for (const float W : Weights) { Total += FMath::Max(0.f, W); }
	if (Total <= 0.f)
	{
		return 0; // all weights zeroed -> behave like the legacy resolver
	}
	float Pick = Stream->FRandRange(0.f, Total);
	for (int32 i = 0; i < Weights.Num(); ++i)
	{
		Pick -= FMath::Max(0.f, Weights[i]);
		if (Pick <= 0.f) { return i; }
	}
	return Weights.Num() - 1; // float-edge fallthrough
}

bool UHexTileSet::FindTileForMask(int32 TargetMask, int32 TargetWaterMask, int32& OutTileIndex, int32& OutRotation,
	const FRandomStream* VariantStream) const
{
	// Collect every tile that can present the target masks, each at its first
	// matching rotation. One candidate per necklace today; blank variants share
	// (0, 0) and are disambiguated by Weight below.
	TArray<int32, TInlineAllocator<8>> CandTile;
	TArray<int32, TInlineAllocator<8>> CandRot;
	TArray<float, TInlineAllocator<8>> CandWeight;
	for (int32 i = 0; i < Tiles.Num(); ++i)
	{
		const int32 Base = TileMask(Tiles[i]);
		const int32 BaseWater = Tiles[i].WaterMask & 0x3F;
		for (int32 r = 0; r < 6; ++r)
		{
			if (HexGrid::RotateMask6(Base, r) == TargetMask &&
				HexGrid::RotateMask6(BaseWater, r) == TargetWaterMask)
			{
				CandTile.Add(i);
				CandRot.Add(r);
				CandWeight.Add(Tiles[i].Weight);
				break;
			}
		}
	}
	if (CandTile.Num() == 0)
	{
		OutTileIndex = INDEX_NONE;
		OutRotation = 0;
		return false;
	}

	const int32 C = PickWeightedCandidate(CandWeight, VariantStream);
	OutTileIndex = CandTile[C];
	OutRotation = CandRot[C];
	// A fully blank cell matches at every rotation, so the heading is free entropy:
	// spin it so repeated garden variants don't read as a stamped lattice.
	if (TargetMask == 0 && TargetWaterMask == 0 && VariantStream)
	{
		OutRotation = VariantStream->RandRange(0, 5);
	}
	return true;
}
