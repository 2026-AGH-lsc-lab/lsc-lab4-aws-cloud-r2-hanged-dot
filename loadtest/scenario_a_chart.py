#!/usr/bin/env python3
"""Generate stacked bar chart for Scenario A cold start analysis."""

import matplotlib.pyplot as plt
import numpy as np
categories = ['Zip\nCold Start', 'Container\nCold Start', 'Zip\nWarm', 'Container\nWarm']

init_duration = [612, 623, 0, 0]
handler_duration = [82, 95, 77, 80]
network_rtt = [540, 520, 26, 24]

fig, ax = plt.subplots(figsize=(10, 6))

x = np.arange(len(categories))
width = 0.6

p1 = ax.bar(x, network_rtt, width, label='Network RTT', color='#3498db')
p2 = ax.bar(x, init_duration, width, bottom=network_rtt, label='Init Duration', color='#e74c3c')
p3 = ax.bar(x, handler_duration, width, bottom=np.array(network_rtt) + np.array(init_duration), 
            label='Handler Duration', color='#2ecc71')

for i, (net, init, handler) in enumerate(zip(network_rtt, init_duration, handler_duration)):
    total = net + init + handler
    if net > 0:
        ax.text(i, net/2, f'{net}ms', ha='center', va='center', fontsize=10, fontweight='bold')
    if init > 0:
        ax.text(i, net + init/2, f'{init}ms', ha='center', va='center', fontsize=10, fontweight='bold')
    ax.text(i, net + init + handler/2, f'{handler}ms', ha='center', va='center', fontsize=10, fontweight='bold')
    ax.text(i, total + 30, f'{total}ms', ha='center', va='bottom', fontsize=11, fontweight='bold')

ax.set_ylabel('Latency (ms)', fontsize=12)
ax.set_title('Lambda Cold Start Latency Decomposition', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(categories, fontsize=11)
ax.legend(loc='upper right', fontsize=10)
ax.set_ylim(0, 1400)
ax.grid(axis='y', alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig('../results/figures/latency-decomposition.png', dpi=150, bbox_inches='tight')
print("Chart saved to results/figures/latency-decomposition.png")