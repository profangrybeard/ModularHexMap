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

	// The fixed core is the EXPLICIT set of authored cells (membership, not a radius — the core
	// can be irregular, e.g. hub + ring + off-axis valley tiles). Their masks are written verbatim
	// and never mutated; the growth only reads their exposed stubs so the frontier connects.
	TSet<FIntPoint> Pinned;
	for (const FHexCellResult& CC : CoreCells) { Pinned.Add(CC.Axial); }
	auto InCore = [&](const FIntPoint& C) { return Pinned.Contains(C); };
	for (const FHexCellResult& CC : CoreCells)
	{
		if (InR(CC.Axial)) { Mask[CC.Axial] = CC.RoadMask; }
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

	// Frontier-walk state is declared up here so an artery can fork a branch straight into it.
	struct FTip { FIntPoint Cell; int32 InEdge; int32 StraightRun = 0; };
	TArray<FTip> Frontier;
	int32 Budget = P.RoadBudget;

	// 1. Cardinal arteries: a straight spine off the core along each chosen axis, then bend/divide
	//    past ArteryStraightRadius out to the map edge. Cells along the way become branch seeds.
	TArray<FIntPoint> Seeds;
	const int32 Axes = P.bCardinalArteries ? FMath::Clamp(P.NumArteries, 0, 3) : 0;
	for (int32 a = 0; a < Axes; ++a)
	{
		const int32 Dirs[2] = { a, (a + 3) % 6 };
		for (int32 d : Dirs)
		{
			// Advance along this axis THROUGH the pinned core to the first frontier cell.
			FIntPoint C(0, 0);
			int32 Adv = 100;
			while (InR(C) && InCore(C) && --Adv > 0) { C = Neighbor(C, d); }
			if (!InR(C)) { continue; } // axis runs off the map while still inside the core
			// Inward connector toward the core (the artery continues out of the core's stub).
			Mask[C] |= (1 << ((d + 3) % 6));
			int32 CurDir = d;
			int32 Guard = 1000;
			while (InR(C) && --Guard > 0)
			{
				int32 StepDir = CurDir;
				// Past the straight spine the artery bends/divides so the avenue feels intentional.
				if (Distance(C) >= P.ArteryStraightRadius)
				{
					if (Budget > 0 && Rng.FRand() < P.ArteryForkChance)
					{
						const int32 Branch = (Rng.FRand() < 0.5f) ? (CurDir + 1) % 6 : (CurDir + 5) % 6;
						if ((Mask[C] & (1 << Branch)) == 0 && MarkRoad(C, Branch))
						{
							Frontier.Add({ Neighbor(C, Branch), (Branch + 3) % 6, 0 });
							--Budget;
						}
					}
					if (Rng.FRand() < P.ArteryKinkChance)
					{
						StepDir = (Rng.FRand() < 0.5f) ? (CurDir + 1) % 6 : (CurDir + 5) % 6;
					}
				}
				MarkRoad(C, StepDir);        // runs off the edge at the boundary cell
				Seeds.AddUnique(C);
				CurDir = StepDir;
				const FIntPoint Nxt = Neighbor(C, StepDir);
				if (!InR(Nxt)) { break; }
				C = Nxt;
			}
		}
	}

	// 2. Secondary branching: sprout side streets off the artery seeds (or from the core
	//    boundary ring when there are no arteries), then random-walk them with the road budget.
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
		// No arteries: branch outward from frontier cells that touch the core, growing away.
		for (const FIntPoint& C : Region)
		{
			if (Budget <= 0) { break; }
			if (InCore(C)) { continue; }
			bool bTouchesCore = false;
			for (int32 e = 0; e < 6; ++e) { if (InCore(Neighbor(C, e))) { bTouchesCore = true; break; } }
			if (!bTouchesCore) { continue; }
			if (Rng.FRand() >= P.BranchChance) { continue; }
			const int32 e = Rng.RandRange(0, 5);
			// Prefer an edge pointing away from the origin (its neighbor is farther out).
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
		const int32 Left = (Straight + 1) % 6;
		const int32 Right = (Straight + 5) % 6;

		// Stacking turn pressure: each consecutive straight segment decays the straight-continue
		// chance, so long straights grow likely to kink (built-in visibility blocking). A hard
		// MaxStraightRun cap forces the turn outright.
		const bool bForceTurn = (P.MaxStraightRun > 0 && T.StraightRun >= P.MaxStraightRun);
		const float StraightProb = bForceTurn
			? 0.f
			: P.StraightBias * FMath::Pow(P.StraightDecay, float(T.StraightRun));

		TArray<int32, TInlineAllocator<4>> Exits;
		auto Consider = [&](int32 e, float Prob)
		{
			if (e != T.InEdge && Rng.FRand() < Prob) { Exits.AddUnique(e); }
		};
		Consider(Straight, StraightProb);
		Consider(Left, P.BranchChance);
		Consider(Right, P.BranchChance);
		if (Exits.Num() == 0)
		{
			// Nothing chosen: a forced turn still kinks (pick a side); otherwise maybe continue
			// straight at the decayed odds, else let the street terminate.
			if (bForceTurn) { Exits.Add(Rng.FRand() < 0.5f ? Left : Right); }
			else if (Rng.FRand() < StraightProb) { Exits.Add(Straight); }
		}

		for (int32 e : Exits)
		{
			if (Budget <= 0) { break; }
			if (MarkRoad(T.Cell, e))
			{
				const int32 NextRun = (e == Straight) ? (T.StraightRun + 1) : 0;
				Frontier.Add({ Neighbor(T.Cell, e), (e + 3) % 6, NextRun });
				--Budget;
			}
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
