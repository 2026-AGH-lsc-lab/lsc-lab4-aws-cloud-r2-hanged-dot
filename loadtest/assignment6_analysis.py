#!/usr/bin/env python3

import matplotlib.pyplot as plt
import numpy as np

PEAK_RPS = 100
PEAK_DURATION_HOURS = 0.5
NORMAL_RPS = 5
NORMAL_DURATION_HOURS = 5.5
IDLE_HOURS = 18

LAMBDA_HANDLER_DURATION_MS = 77  
LAMBDA_MEMORY_MB = 512
LAMBDA_MEMORY_GB = LAMBDA_MEMORY_MB / 1024
LAMBDA_REQUEST_COST_PER_MILLION = 0.20
LAMBDA_GB_SECOND_COST = 0.0000166667

FARGATE_HOURLY_RATE = 0.02469
EC2_HOURLY_RATE = 0.0208

def calculate_monthly_requests():
    days_per_month = 30
    peak_requests_per_day = PEAK_RPS * PEAK_DURATION_HOURS * 3600
    peak_requests_per_month = peak_requests_per_day * days_per_month
    normal_requests_per_day = NORMAL_RPS * NORMAL_DURATION_HOURS * 3600
    normal_requests_per_month = normal_requests_per_day * days_per_month
    total_requests_per_month = peak_requests_per_month + normal_requests_per_month
    
    return {
        'peak_per_day': peak_requests_per_day,
        'peak_per_month': peak_requests_per_month,
        'normal_per_day': normal_requests_per_day,
        'normal_per_month': normal_requests_per_month,
        'total_per_month': total_requests_per_month
    }

def calculate_lambda_cost(requests_per_month):
    """Calculate Lambda monthly cost."""
    # Request cost
    request_cost = (requests_per_month / 1_000_000) * LAMBDA_REQUEST_COST_PER_MILLION
    
    # Compute cost
    duration_seconds = LAMBDA_HANDLER_DURATION_MS / 1000
    gb_seconds = requests_per_month * duration_seconds * LAMBDA_MEMORY_GB
    compute_cost = gb_seconds * LAMBDA_GB_SECOND_COST
    
    total_cost = request_cost + compute_cost
    
    return {
        'request_cost': request_cost,
        'compute_cost': compute_cost,
        'total_cost': total_cost,
        'gb_seconds': gb_seconds
    }

def calculate_always_on_cost(hourly_rate):
    """Calculate monthly cost for always-on services."""
    hours_per_month = 24 * 30
    return hourly_rate * hours_per_month

def find_break_even_rps(hourly_rate):
    """
    Find the average RPS where Lambda cost equals always-on cost.
    
    Lambda cost = (requests/month × $0.20/1M) + (GB-seconds/month × $0.0000166667)
    Always-on cost = hourly_rate × 24 × 30
    
    Let R = requests/month
    R = avg_RPS × seconds_per_month
    seconds_per_month = 30 × 24 × 3600 = 2,592,000
    
    Lambda cost = (R × 0.20/1M) + (R × duration_s × memory_GB × 0.0000166667)
    Lambda cost = R × (0.20/1M + duration_s × memory_GB × 0.0000166667)
    
    Set Lambda cost = Always-on cost:
    R × (0.20/1M + duration_s × memory_GB × 0.0000166667) = hourly_rate × 720
    
    R = (hourly_rate × 720) / (0.20/1M + duration_s × memory_GB × 0.0000166667)
    
    avg_RPS = R / seconds_per_month
    """
    seconds_per_month = 30 * 24 * 3600
    hours_per_month = 24 * 30
    duration_seconds = LAMBDA_HANDLER_DURATION_MS / 1000
    
    always_on_cost = hourly_rate * hours_per_month
    cost_per_request = (LAMBDA_REQUEST_COST_PER_MILLION / 1_000_000) + (duration_seconds * LAMBDA_MEMORY_GB * LAMBDA_GB_SECOND_COST)
    requests_at_break_even = always_on_cost / cost_per_request
    avg_rps = requests_at_break_even / seconds_per_month
    
    return {
        'avg_rps': avg_rps,
        'requests_per_month': requests_at_break_even,
        'monthly_cost': always_on_cost
    }

def generate_cost_chart():
    rps_range = np.linspace(0, 20, 1000)
    seconds_per_month = 30 * 24 * 3600
    lambda_costs = []
    for rps in rps_range:
        requests_per_month = rps * seconds_per_month
        cost = calculate_lambda_cost(requests_per_month)['total_cost']
        lambda_costs.append(cost)
    
    fargate_cost = calculate_always_on_cost(FARGATE_HOURLY_RATE)
    ec2_cost = calculate_always_on_cost(EC2_HOURLY_RATE)
    fargate_breakeven = find_break_even_rps(FARGATE_HOURLY_RATE)
    ec2_breakeven = find_break_even_rps(EC2_HOURLY_RATE)
    plt.figure(figsize=(12, 7))
    
    plt.plot(rps_range, lambda_costs, 'b-', linewidth=2, label='Lambda (Zip, 512MB)')
    plt.axhline(y=fargate_cost, color='orange', linestyle='--', linewidth=2, label=f'Fargate (0.5 vCPU, 1GB) - ${fargate_cost:.2f}/month')
    plt.axhline(y=ec2_cost, color='green', linestyle='--', linewidth=2, label=f'EC2 t3.small - ${ec2_cost:.2f}/month')
    
    plt.plot(fargate_breakeven['avg_rps'], fargate_breakeven['monthly_cost'], 
             'ro', markersize=10, label=f'Fargate Break-Even: {fargate_breakeven["avg_rps"]:.1f} RPS')
    plt.plot(ec2_breakeven['avg_rps'], ec2_breakeven['monthly_cost'], 
             'go', markersize=10, label=f'EC2 Break-Even: {ec2_breakeven["avg_rps"]:.1f} RPS')
    
    requests = calculate_monthly_requests()
    current_avg_rps = requests['total_per_month'] / seconds_per_month
    current_lambda_cost = calculate_lambda_cost(requests['total_per_month'])['total_cost']
    plt.plot(current_avg_rps, current_lambda_cost, 'bs', markersize=12, label=f'Current Traffic Model: {current_avg_rps:.2f} RPS')
    plt.xlabel('Average RPS (Requests Per Second)', fontsize=12, fontweight='bold')
    plt.ylabel('Monthly Cost (USD)', fontsize=12, fontweight='bold')
    plt.title('Cost vs. Average RPS: Lambda vs. Always-On Services', fontsize=14, fontweight='bold')
    plt.legend(loc='upper left', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 20)
    plt.ylim(0, max(fargate_cost, ec2_cost) * 1.2)
    
    plt.annotate(f'Fargate Break-even:\n{fargate_breakeven["avg_rps"]:.2f} RPS',
                xy=(fargate_breakeven['avg_rps'], fargate_breakeven['monthly_cost']),
                xytext=(fargate_breakeven['avg_rps'] + 3, fargate_breakeven['monthly_cost'] + 1),
                arrowprops=dict(arrowstyle='->', color='red', lw=1.5),
                fontsize=9, bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.7))
    plt.annotate(f'EC2 Break-even:\n{ec2_breakeven["avg_rps"]:.2f} RPS',
                xy=(ec2_breakeven['avg_rps'], ec2_breakeven['monthly_cost']),
                xytext=(ec2_breakeven['avg_rps'] + 3, ec2_breakeven['monthly_cost'] - 2),
                arrowprops=dict(arrowstyle='->', color='green', lw=1.5),
                fontsize=9, bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgreen', alpha=0.7))
    plt.annotate(f'Current Traffic:\n{current_avg_rps:.2f} RPS\n${current_lambda_cost:.2f}/mo',
                xy=(current_avg_rps, current_lambda_cost),
                xytext=(current_avg_rps - 1, current_lambda_cost + 3),
                arrowprops=dict(arrowstyle='->', color='blue', lw=1.5),
                fontsize=9, bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.7))
    
    plt.tight_layout()
    plt.savefig('results/figures/cost_vs_rps.png', dpi=300, bbox_inches='tight')
    
    return {
        'fargate_breakeven': fargate_breakeven,
        'ec2_breakeven': ec2_breakeven,
        'current_avg_rps': current_avg_rps,
        'current_lambda_cost': current_lambda_cost
    }

def main():
    print("=" * 70)
    print("Assignment 6: Cost Model, Break-Even, and Recommendation")
    print("=" * 70)

    print("\n1. TRAFFIC MODEL ANALYSIS")
    print("-" * 70)
    requests = calculate_monthly_requests()
    print(f"Peak traffic:   {PEAK_RPS} RPS × {PEAK_DURATION_HOURS} hours/day = {requests['peak_per_day']:,.0f} requests/day")
    print(f"                → {requests['peak_per_month']:,.0f} requests/month")
    print(f"Normal traffic: {NORMAL_RPS} RPS × {NORMAL_DURATION_HOURS} hours/day = {requests['normal_per_day']:,.0f} requests/day")
    print(f"                → {requests['normal_per_month']:,.0f} requests/month")
    print(f"Idle:           {IDLE_HOURS} hours/day (0 RPS)")
    print(f"\nTotal requests/month: {requests['total_per_month']:,.0f}")
    
    seconds_per_month = 30 * 24 * 3600
    avg_rps = requests['total_per_month'] / seconds_per_month
    print(f"Average RPS: {avg_rps:.2f}")
    print("\n2. LAMBDA MONTHLY COST")
    print("-" * 70)
    lambda_cost = calculate_lambda_cost(requests['total_per_month'])
    print(f"Configuration: {LAMBDA_MEMORY_MB} MB memory, {LAMBDA_HANDLER_DURATION_MS} ms p50 duration")
    print(f"Request cost:  {requests['total_per_month']:,.0f} requests × ${LAMBDA_REQUEST_COST_PER_MILLION}/1M = ${lambda_cost['request_cost']:.2f}")
    print(f"Compute cost:  {lambda_cost['gb_seconds']:,.0f} GB-seconds × ${LAMBDA_GB_SECOND_COST} = ${lambda_cost['compute_cost']:.2f}")
    print(f"Total Lambda cost: ${lambda_cost['total_cost']:.2f}/month")
    print("\n3. ALWAYS-ON MONTHLY COSTS")
    print("-" * 70)
    fargate_cost = calculate_always_on_cost(FARGATE_HOURLY_RATE)
    ec2_cost = calculate_always_on_cost(EC2_HOURLY_RATE)
    print(f"Fargate: ${FARGATE_HOURLY_RATE}/hour × 720 hours = ${fargate_cost:.2f}/month")
    print(f"EC2:     ${EC2_HOURLY_RATE}/hour × 720 hours = ${ec2_cost:.2f}/month")
    print("\n4. BREAK-EVEN ANALYSIS")
    print("-" * 70)
    fargate_breakeven = find_break_even_rps(FARGATE_HOURLY_RATE)
    ec2_breakeven = find_break_even_rps(EC2_HOURLY_RATE)
    
    print(f"\nFargate Break-Even:")
    print(f"  Average RPS: {fargate_breakeven['avg_rps']:.2f}")
    print(f"  Requests/month: {fargate_breakeven['requests_per_month']:,.0f}")
    print(f"  Monthly cost: ${fargate_breakeven['monthly_cost']:.2f}")
    
    print(f"\nEC2 Break-Even:")
    print(f"  Average RPS: {ec2_breakeven['avg_rps']:.2f}")
    print(f"  Requests/month: {ec2_breakeven['requests_per_month']:,.0f}")
    print(f"  Monthly cost: ${ec2_breakeven['monthly_cost']:.2f}")
    
    print("\n5. BREAK-EVEN ALGEBRA")
    print("-" * 70)
    print("Lambda cost = (R × $0.20/1M) + (R × duration_s × memory_GB × $0.0000166667)")
    print("Always-on cost = hourly_rate × 24 × 30")
    print("\nAt break-even: Lambda cost = Always-on cost")
    print(f"\nFor Fargate (${FARGATE_HOURLY_RATE}/hour):")
    print(f"  R × (0.20/1M + {LAMBDA_HANDLER_DURATION_MS/1000} × {LAMBDA_MEMORY_GB} × 0.0000166667) = {FARGATE_HOURLY_RATE} × 720")
    print(f"  R × {(LAMBDA_REQUEST_COST_PER_MILLION/1_000_000 + (LAMBDA_HANDLER_DURATION_MS/1000)*LAMBDA_MEMORY_GB*LAMBDA_GB_SECOND_COST):.10f} = {fargate_cost:.2f}")
    print(f"  R = {fargate_breakeven['requests_per_month']:,.0f} requests/month")
    print(f"  avg_RPS = {fargate_breakeven['avg_rps']:.2f}")
    
    print(f"\nFor EC2 (${EC2_HOURLY_RATE}/hour):")
    print(f"  R × {(LAMBDA_REQUEST_COST_PER_MILLION/1_000_000 + (LAMBDA_HANDLER_DURATION_MS/1000)*LAMBDA_MEMORY_GB*LAMBDA_GB_SECOND_COST):.10f} = {ec2_cost:.2f}")
    print(f"  R = {ec2_breakeven['requests_per_month']:,.0f} requests/month")
    print(f"  avg_RPS = {ec2_breakeven['avg_rps']:.2f}")
    
    print("\n6. GENERATING COST VS RPS CHART")
    print("-" * 70)
    chart_data = generate_cost_chart()
    
    print("\n7. COST COMPARISON SUMMARY")
    print("-" * 70)
    print(f"Current traffic model ({avg_rps:.2f} avg RPS):")
    print(f"  Lambda:  ${lambda_cost['total_cost']:.2f}/month")
    print(f"  Fargate: ${fargate_cost:.2f}/month ({fargate_cost/lambda_cost['total_cost']:.1f}× more expensive)")
    print(f"  EC2:     ${ec2_cost:.2f}/month ({ec2_cost/lambda_cost['total_cost']:.1f}× more expensive)")
    
    print("\n" + "=" * 70)
    print("Analysis complete!")
    print("=" * 70)

if __name__ == '__main__':
    main()

