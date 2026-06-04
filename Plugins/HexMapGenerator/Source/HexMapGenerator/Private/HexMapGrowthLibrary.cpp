// Copyright (c) 2026. All rights reserved.

#include "HexMapGrowthLibrary.h"
#include "HexCoordinates.h"

FHexNetwork UHexMapGrowthLibrary::GrowRoadNetwork(const FHexGrowthParams& P, const TArray<FHexCellResult>& CoreCells, int32 Seed)
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

	// The fixed core: cells with Distance <= CoreRadius are PINNED. Their masks come from the
	// authored CoreCells (the Pit + story ring); the growth never writes to them — it only
	// reads their exposed stubs so the frontier connects to the core by construction.
	const int32 CoreR = FMath::Max(0, P.CoreRadius);
	auto InCore = [&](const FIntPoint& C) { return Distance(C) <= CoreR; };
	for (const FHexCellResult& CC : CoreCells)
	{
		if (InR(CC.Axial) && InCore(CC.Axial)) { Mask[CC.Axial] = CC.RoadMask; }
	}

	// Mark a road on edge e of C, plus the mutual return edge on the neighbor if it is
	// in-region. Returns true when the road continues into the map (neighbor in-region);
	// false means it runs off the map edge (still drawn on C, just no neighbor). Core cells
	// are immutable: we never write their masks (they keep their authored values), though a
	// frontier road may still abut and "dead-end into" the core (e.g. a street into the Pit).
	auto MarkRoad = [&](const FIntPoint& C, int32 e) -> bool
	{
		if (!InR(C) || InCore(C)) { return false; }
		Mask[C] |= (1 << e);
		const FIntPoint N = Neighbor(C, e);
		if (InR(N)) { if (!InCore(N)) { Mask[N] |= (1 << ((e + 3) % 6)); } return true; }
		return false;
	};

	// 1. Cardinal arteries: a straight road along each chosen axis, running from the core
	//    boundary (ring CoreRadius+1) out to both map edges. The first frontier cell also gets
	//    an inward stub toward the core, so the artery connects to the Pit's story ring. Cells
	//    along the way become branch seeds (intersection seeds).
	TArray<FIntPoint> Seeds;
	const int32 Axes = P.bCardinalArteries ? FMath::Clamp(P.NumArteries, 0, 3) : 0;
	for (int32 a = 0; a < Axes; ++a)
	{
		const int32 Dirs[2] = { a, (a + 3) % 6 };
		for (int32 d : Dirs)
		{
			// Step out of the core to the first frontier cell along this axis.
			FIntPoint C(0, 0);
			for (int32 s = 0; s <= CoreR; ++s) { C = Neighbor(C, d); }
			// Inward connector toward the core boundary (a street leading to the Pit's ring).
			if (InR(C) && !InCore(C)) { Mask[C] |= (1 << ((d + 3) % 6)); }
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

	// 2. Secondary branching: sprout side streets off the artery seeds (or from the core
	//    boundary ring when there are no arteries), then random-walk them with the road budget.
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
		// No arteries: branch outward from the core boundary instead of the (now pinned) Pit.
		// Seed from each frontier cell just outside the core, growing away from it.
		for (const FIntPoint& C : Region)
		{
			if (Budget <= 0) { break; }
			if (InCore(C) || Distance(C) != CoreR + 1) { continue; }
			if (Rng.FRand() >= P.BranchChance) { continue; }
			const int32 e = Rng.RandRange(0, 5);
			// Prefer an edge pointing away from the core (its neighbor is farther out).
			const int32 Out = (Distance(Neighbor(C, e)) > Distance(C)) ? e : (e + 3) % 6;
			if ((Mask[C] & (1 << Out)) == 0 && MarkRoad(C, Out))
			{
				Frontier.Add({ Neighbor(C, Out), (Out + 3) % 6 });
				--Budget;
			}
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

TArray<FHexCellResult> UHexMapGrowthLibrary::MakePlaceholderCore(const FHexGrowthParams& P)
{
	using namespace HexGrid;
	TArray<FHexCellResult> Core;
	const int32 CoreR = FMath::Max(0, P.CoreRadius);

	// Every cell within the core radius, blank by default (story tiles, no roads yet).
	for (int32 q = -CoreR; q <= CoreR; ++q)
	{
		for (int32 r = -CoreR; r <= CoreR; ++r)
		{
			const FIntPoint C(q, r);
			if (Distance(C) <= CoreR)
			{
				FHexCellResult Cell;
				Cell.Axial = C;
				Cell.RoadMask = 0; // Pit + blank ring; the Pit is a terminus (no through-road).
				Core.Add(Cell);
			}
		}
	}

	// On each chosen artery axis, give the boundary core cell a straight road: inward toward the
	// Pit (a street that dead-ends at the rim) + outward to meet the frontier artery.
	const int32 Axes = P.bCardinalArteries ? FMath::Clamp(P.NumArteries, 0, 3) : 0;
	for (int32 a = 0; a < Axes; ++a)
	{
		const int32 Dirs[2] = { a, (a + 3) % 6 };
		for (int32 d : Dirs)
		{
			// Boundary core cell along this axis = CoreR steps out from the Pit.
			FIntPoint C(0, 0);
			for (int32 s = 0; s < CoreR; ++s) { C = Neighbor(C, d); }
			const int32 StraightMask = (1 << d) | (1 << ((d + 3) % 6));
			for (FHexCellResult& Cell : Core)
			{
				if (Cell.Axial == C) { Cell.RoadMask |= StraightMask; break; }
			}
		}
	}

	return Core;
}
