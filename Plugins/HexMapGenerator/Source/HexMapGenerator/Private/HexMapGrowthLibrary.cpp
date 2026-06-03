// Copyright (c) 2026. All rights reserved.

#include "HexMapGrowthLibrary.h"
#include "HexCoordinates.h"

FHexNetwork UHexMapGrowthLibrary::GrowRoadNetwork(const FHexGrowthParams& P, int32 Seed)
{
	using namespace HexGrid;
	FRandomStream Rng(Seed);

	// Build the hex region (disk of the given radius) and a per-cell road mask.
	TSet<FIntPoint> Region;
	TMap<FIntPoint, int32> Mask;
	for (int32 q = -P.Radius; q <= P.Radius; ++q)
	{
		for (int32 r = -P.Radius; r <= P.Radius; ++r)
		{
			const FIntPoint C(q, r);
			if (Distance(C) <= P.Radius)
			{
				Region.Add(C);
				Mask.Add(C, 0);
			}
		}
	}

	auto InR = [&](const FIntPoint& C) { return Region.Contains(C); };

	// Mark a road on edge e of C, plus the mutual return edge on the neighbor if it is
	// in-region. Returns true when the road continues into the map (neighbor in-region);
	// false means it runs off the map edge (still drawn on C, just no neighbor).
	auto MarkRoad = [&](const FIntPoint& C, int32 e) -> bool
	{
		if (!InR(C)) { return false; }
		Mask[C] |= (1 << e);
		const FIntPoint N = Neighbor(C, e);
		if (InR(N)) { Mask[N] |= (1 << ((e + 3) % 6)); return true; }
		return false;
	};

	// 1. Cardinal arteries: a straight road along each chosen axis, from the center out to
	//    both map edges. Cells along the way become branch seeds (intersection seeds).
	TArray<FIntPoint> Seeds;
	const int32 Axes = P.bCardinalArteries ? FMath::Clamp(P.NumArteries, 0, 3) : 0;
	for (int32 a = 0; a < Axes; ++a)
	{
		const int32 Dirs[2] = { a, (a + 3) % 6 };
		for (int32 d : Dirs)
		{
			FIntPoint C(0, 0);
			int32 Guard = 1000;
			while (InR(C) && --Guard > 0)
			{
				MarkRoad(C, d);             // runs off the edge at the boundary cell
				Seeds.AddUnique(C);
				const FIntPoint Nxt = Neighbor(C, d);
				if (!InR(Nxt)) { break; }
				C = Nxt;
			}
		}
	}

	// 2. Secondary branching: sprout side streets off the artery seeds (or from the origin
	//    when there are no arteries), then random-walk them with the road budget.
	struct FTip { FIntPoint Cell; int32 InEdge; };
	TArray<FTip> Frontier;
	int32 Budget = P.RoadBudget;

	if (Seeds.Num() > 0)
	{
		for (const FIntPoint& C : Seeds)
		{
			if (Budget <= 0) { break; }
			if (Rng.FRand() < P.BranchChance)
			{
				const int32 e = Rng.RandRange(0, 5);
				if ((Mask[C] & (1 << e)) == 0 && MarkRoad(C, e))
				{
					Frontier.Add({ Neighbor(C, e), (e + 3) % 6 });
					--Budget;
				}
			}
		}
	}
	else
	{
		const FIntPoint Start(0, 0);
		const int32 e = Rng.RandRange(0, 5);
		if (MarkRoad(Start, e)) { Frontier.Add({ Neighbor(Start, e), (e + 3) % 6 }); --Budget; }
		if (Rng.FRand() < 0.7f)
		{
			const int32 e2 = (e + 3) % 6;
			if (MarkRoad(Start, e2)) { Frontier.Add({ Neighbor(Start, e2), (e2 + 3) % 6 }); --Budget; }
		}
	}

	int32 Guard = 100000;
	while (Frontier.Num() > 0 && Budget > 0 && --Guard > 0)
	{
		const int32 Idx = Rng.RandRange(0, Frontier.Num() - 1);
		const FTip T = Frontier[Idx];
		Frontier.RemoveAtSwap(Idx);

		const int32 Straight = (T.InEdge + 3) % 6;
		TArray<int32, TInlineAllocator<4>> Exits;
		auto Consider = [&](int32 e, float Prob)
		{
			if (e != T.InEdge && Rng.FRand() < Prob) { Exits.AddUnique(e); }
		};
		Consider(Straight, P.StraightBias);
		Consider((Straight + 1) % 6, P.BranchChance);
		Consider((Straight + 5) % 6, P.BranchChance);
		if (Exits.Num() == 0 && Rng.FRand() < P.StraightBias) { Exits.Add(Straight); }

		for (int32 e : Exits)
		{
			if (Budget <= 0) { break; }
			if (MarkRoad(T.Cell, e)) { Frontier.Add({ Neighbor(T.Cell, e), (e + 3) % 6 }); --Budget; }
		}
	}

	FHexNetwork Net;
	Net.Cells.Reserve(Region.Num());
	for (const FIntPoint& C : Region)
	{
		FHexCellResult R;
		R.Axial = C;
		R.RoadMask = Mask[C];
		Net.Cells.Add(R);
	}
	return Net;
}
