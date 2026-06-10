// Copyright (c) 2026. All rights reserved.

#include "HexTileSet.h"
#include "HexCoordinates.h"

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

bool UHexTileSet::FindTileForMask(int32 TargetMask, int32 TargetWaterMask, int32& OutTileIndex, int32& OutRotation) const
{
	for (int32 i = 0; i < Tiles.Num(); ++i)
	{
		const int32 Base = TileMask(Tiles[i]);
		const int32 BaseWater = Tiles[i].WaterMask & 0x3F;
		for (int32 r = 0; r < 6; ++r)
		{
			if (HexGrid::RotateMask6(Base, r) == TargetMask &&
				HexGrid::RotateMask6(BaseWater, r) == TargetWaterMask)
			{
				OutTileIndex = i;
				OutRotation = r;
				return true;
			}
		}
	}
	OutTileIndex = INDEX_NONE;
	OutRotation = 0;
	return false;
}
