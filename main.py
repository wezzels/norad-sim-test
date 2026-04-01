"""Main simulation runner."""

import argparse
import time
import json
from pathlib import Path

from simulator import GameState, DefenseManager, DetectionManager, ScenarioLoader, HumanPlayer


def run_simulation(scenario_id: str = "tutorial", verbose: bool = False, human_mode: bool = True):
    """
    Run a simulation.
    
    Args:
        scenario_id: Scenario to run
        verbose: Print detailed output
        human_mode: Use human-like AI player
    """
    # Initialize
    game_state = GameState()
    game_state.load_data("data")
    
    defense_manager = DefenseManager(game_state)
    detection_manager = DetectionManager()
    scenario_loader = ScenarioLoader()
    
    # Create human player if requested
    player = None
    if human_mode:
        player = HumanPlayer(game_state, defense_manager, detection_manager)
    
    # Load scenario
    scenario = scenario_loader.load_scenario(scenario_id)
    if not scenario:
        print(f"Scenario '{scenario_id}' not found!")
        return None
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario.name}")
        print(f"Difficulty: {'★' * scenario.difficulty}")
        print(f"Waves: {len(scenario.waves)}")
        print(f"Interceptors: GBI={scenario.interceptors.get('GBI', 0)}, "
              f"THAAD={scenario.interceptors.get('THAAD', 0)}, "
              f"Patriot={scenario.interceptors.get('Patriot', 0)}")
        print(f"{'='*60}\n")
    
    # Set up interceptor inventory
    defense_manager.reset_inventory(scenario.interceptors)
    
    # Start scenario
    scenario_loader.start_scenario()
    game_state.resume()
    
    # Simulation loop
    last_time = time.time()
    frame_count = 0
    actions_taken = []
    
    while not scenario_loader.is_complete() or len(game_state.missiles) > 0:
        # Calculate delta
        current_time = time.time()
        delta = min(0.1, current_time - last_time)  # Cap at 100ms
        last_time = current_time
        
        # Update scenario (spawn missiles)
        new_missiles = scenario_loader.update(game_state.simulation_time)
        for missile_data in new_missiles:
            game_state.launch_missile(
                missile_data.get("origin", "Unknown"),
                missile_data.get("target", "Unknown"),
                missile_data.get("type", "ICBM")
            )
            if verbose:
                print(f"[{game_state.simulation_time:.1f}s] "
                      f"Missile launched: {missile_data.get('origin')} -> {missile_data.get('target')}")
        
        # Detect missiles
        detections = detection_manager.detect_missiles(
            game_state.missiles, 
            game_state.simulation_time
        )
        for det in detections:
            if verbose:
                print(f"[{game_state.simulation_time:.1f}s] "
                      f"Detected by {det['satellite']}: {det['missile_id']}")
        
        # Human player makes decisions
        if player:
            actions = player.update(delta)
            for action in actions:
                actions_taken.append(action)
                if verbose:
                    print(f"[{game_state.simulation_time:.1f}s] "
                          f"Launched {action['interceptor_type']} at {action['missile_id'][:15]}... "
                          f"(reaction: {action['reaction_time']:.2f}s, stress: {action['stress']:.2f})")
        
        # Update game state
        game_state.update(delta)
        
        # Check for end conditions
        if game_state.stats["cities_hit"] >= 3:
            if verbose:
                print(f"\n{'='*60}")
                print("SIMULATION FAILED - Too many cities hit")
                print(f"{'='*60}")
            break
        
        # Increment frame
        frame_count += 1
    
    # Results
    results = {
        "scenario": scenario_id,
        "completed": scenario_loader.is_complete(),
        "missiles_launched": game_state.stats["missiles_launched"],
        "missiles_intercepted": game_state.stats["missiles_intercepted"],
        "cities_hit": game_state.stats["cities_hit"],
        "final_defcon": game_state.current_defcon,
        "simulation_time": game_state.simulation_time,
        "interceptors_remaining": defense_manager.get_inventory_status(),
        "player_stats": player.get_stats() if player else None
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print("SIMULATION COMPLETE")
        print(f"{'='*60}")
        print(f"Missiles Launched: {results['missiles_launched']}")
        print(f"Missiles Intercepted: {results['missiles_intercepted']}")
        print(f"Intercept Rate: {results['missiles_intercepted']/max(1, results['missiles_launched'])*100:.1f}%")
        print(f"Cities Hit: {results['cities_hit']}")
        print(f"Final DEFCON: {results['final_defcon']}")
        print(f"Simulation Time: {results['simulation_time']:.1f}s")
        if player:
            print(f"\nPlayer Stats:")
            print(f"  Games Played: {player.memory.games_played + 1}")
            print(f"  Avg Reaction Time: {player.memory.avg_reaction_time:.2f}s")
            print(f"  Decisions Made: {player.decisions_made}")
            print(f"{'='*60}")
    
    # Record result
    if player:
        player.record_game_result(results['cities_hit'] < 3)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="NORAD War Simulator - Human Emulation Test")
    parser.add_argument("--scenario", "-s", default="tutorial", help="Scenario ID to run")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--human-mode", action="store_true", default=True, help="Use human-like AI")
    parser.add_argument("--list-scenarios", "-l", action="store_true", help="List available scenarios")
    parser.add_argument("--runs", "-n", type=int, default=1, help="Number of runs")
    
    args = parser.parse_args()
    
    # List scenarios
    if args.list_scenarios:
        loader = ScenarioLoader()
        scenarios = loader.get_available_scenarios()
        print("\nAvailable Scenarios:")
        print("-" * 60)
        for s in scenarios:
            difficulty = "★" * s["difficulty"]
            print(f"{s['id']:20} {s['name']:25} {difficulty}")
            print(f"{'':20} {s['description']}")
            print(f"{'':20} Waves: {s['waves']}")
            print()
        return
    
    # Run simulation(s)
    all_results = []
    
    for run in range(args.runs):
        if args.runs > 1:
            print(f"\n{'='*60}")
            print(f"RUN {run + 1}/{args.runs}")
            print(f"{'='*60}")
        
        results = run_simulation(
            scenario_id=args.scenario,
            verbose=args.verbose,
            human_mode=args.human_mode
        )
        
        if results:
            all_results.append(results)
    
    # Summary if multiple runs
    if args.runs > 1 and all_results:
        print(f"\n{'='*60}")
        print("SUMMARY")
        print(f"{'='*60}")
        
        wins = sum(1 for r in all_results if r["cities_hit"] < 3)
        avg_intercept_rate = sum(
            r["missiles_intercepted"]/max(1, r["missiles_launched"]) 
            for r in all_results
        ) / len(all_results) * 100
        
        print(f"Runs: {args.runs}")
        print(f"Wins: {wins} ({wins/args.runs*100:.1f}%)")
        print(f"Average Intercept Rate: {avg_intercept_rate:.1f}%")
        print(f"Average Cities Hit: {sum(r['cities_hit'] for r in all_results)/len(all_results):.1f}")
        
        if all_results[0].get("player_stats"):
            avg_reaction = sum(
                r["player_stats"]["avg_reaction_time"] 
                for r in all_results if r["player_stats"]
            ) / len(all_results)
            print(f"Average Reaction Time: {avg_reaction:.2f}s")


if __name__ == "__main__":
    main()