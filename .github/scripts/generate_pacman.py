#!/usr/bin/env python3
"""
Generate animated Pac-Man contribution graph SVG
"""
import argparse
import os
import requests
from datetime import datetime, timedelta
import json

def get_contributions(username, token=None):
    """Fetch contribution data from GitHub API"""
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    
    # GraphQL query to get contribution data
    query = """
    query($username: String!) {
      user(login: $username) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    
    variables = {"username": username}
    
    response = requests.post(
        'https://api.github.com/graphql',
        json={'query': query, 'variables': variables},
        headers=headers,
        timeout=30
    )
    
    if response.status_code != 200:
        error_msg = f"API request failed: {response.status_code}"
        try:
            error_data = response.json()
            if 'message' in error_data:
                error_msg += f" - {error_data['message']}"
        except:
            error_msg += f" - {response.text[:200]}"
        raise Exception(error_msg)
    
    data = response.json()
    if 'errors' in data:
        error_details = '; '.join([str(e.get('message', e)) for e in data['errors']])
        raise Exception(f"GraphQL errors: {error_details}")
    
    if not data.get('data') or not data['data'].get('user'):
        raise Exception(f"User '{username}' not found or has no contribution data")
    
    return data['data']['user']['contributionsCollection']['contributionCalendar']

def generate_svg(contributions, theme='light'):
    """Generate animated Pac-Man SVG"""
    weeks = contributions['weeks']
    total_contributions = contributions['totalContributions']
    
    # Colors
    if theme == 'dark':
        bg_color = '#0d1117'
        grid_color = '#161b22'
        dot_color = '#39d353'
        pacman_color = '#ffd700'
        text_color = '#c9d1d9'
    else:
        bg_color = '#ffffff'
        grid_color = '#ebedf0'
        dot_color = '#40c463'
        pacman_color = '#ffd700'
        text_color = '#24292f'
    
    # Calculate grid dimensions
    num_weeks = len(weeks)
    days_per_week = 7
    cell_size = 11
    cell_gap = 2
    cell_total = cell_size + cell_gap
    
    width = num_weeks * cell_total + 20
    height = days_per_week * cell_total + 60
    
    # Build contribution grid
    grid = []
    max_contributions = 0
    for week in weeks:
        week_data = []
        for day in week['contributionDays']:
            count = day['contributionCount']
            week_data.append(count)
            max_contributions = max(max_contributions, count)
        grid.append(week_data)
    
    # Normalize contributions (0-4 levels)
    normalized_grid = []
    for week in grid:
        normalized_week = []
        for count in week:
            if count == 0:
                level = 0
            elif count <= max_contributions * 0.25:
                level = 1
            elif count <= max_contributions * 0.5:
                level = 2
            elif count <= max_contributions * 0.75:
                level = 3
            else:
                level = 4
            normalized_week.append(level)
        normalized_grid.append(normalized_week)
    
    # Calculate animation duration (20 seconds for full journey)
    animation_duration = 20
    pacman_row = 3  # Row where Pac-Man moves (middle row)
    
    # Generate SVG
    svg_parts = []
    svg_parts.append(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" style="background-color: {bg_color};">
  <defs>
    <style>
      .pacman-group {{
        animation: pacman-move {animation_duration}s linear infinite;
      }}
      @keyframes pacman-move {{
        0% {{ transform: translateX(0); }}
        100% {{ transform: translateX({(num_weeks - 1) * cell_total}px); }}
      }}
      @keyframes pacman-mouth {{
        0% {{ transform: rotate(0deg); }}
        50% {{ transform: rotate(45deg); }}
        100% {{ transform: rotate(0deg); }}
      }}
      .pacman-mouth {{
        animation: pacman-mouth 0.15s ease-in-out infinite;
        transform-origin: 5.5px 5.5px;
      }}
    </style>
  </defs>
  <text x="10" y="20" font-family="Arial, sans-serif" font-size="14" fill="{text_color}">
    {total_contributions} contributions in the last year
  </text>
  <g transform="translate(10, 40)">''')
    
    # Draw grid and collect dots for animation
    dots_to_animate = []
    for week_idx, week in enumerate(normalized_grid):
        for day_idx, level in enumerate(week):
            x = week_idx * cell_total
            y = day_idx * cell_total
            
            # Draw cell
            if level > 0:
                intensity = level / 4.0
                if theme == 'light':
                    # Light theme: green shades
                    r = int(64 + (67 - 64) * intensity)
                    g = int(196 + (199 - 196) * intensity)
                    b = int(99 + (102 - 99) * intensity)
                    color = f'rgb({r}, {g}, {b})'
                else:
                    # Dark theme: green shades
                    r = int(57)
                    g = int(57 + (83 - 57) * intensity)
                    b = int(83)
                    color = f'rgb({r}, {g}, {b})'
                
                svg_parts.append(f'''    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" rx="2"/>''')
                
                # Store dot info for animation (only in Pac-Man's row)
                if day_idx == pacman_row:
                    dot_x = x + cell_size / 2
                    dot_y = y + cell_size / 2
                    # Calculate when Pac-Man reaches this dot (based on position)
                    dot_time = (week_idx * cell_total) / ((num_weeks - 1) * cell_total) * animation_duration
                    dots_to_animate.append((dot_x, dot_y, dot_time))
            else:
                svg_parts.append(f'''    <rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{grid_color}" rx="2"/>''')
    
    # Add dots with fade-out animation when Pac-Man reaches them
    for dot_x, dot_y, dot_time in dots_to_animate:
        svg_parts.append(f'''    <circle cx="{dot_x}" cy="{dot_y}" r="1.5" fill="{dot_color}" opacity="1">
      <animate attributeName="opacity" values="1;1;0;0" dur="{animation_duration}s" 
               keyTimes="0;{max(0, (dot_time - 0.1) / animation_duration)};{min(1, (dot_time + 0.1) / animation_duration)};1" 
               repeatCount="indefinite"/>
    </circle>''')
    
    # Add Pac-Man with animated mouth
    pacman_y = pacman_row * cell_total + cell_size / 2
    svg_parts.append(f'''    <g class="pacman-group" transform="translate(0, {pacman_row * cell_total})">
      <circle cx="5.5" cy="5.5" r="5.5" fill="{pacman_color}"/>
      <g class="pacman-mouth">
        <path d="M 5.5 5.5 L 5.5 0 A 5.5 5.5 0 0 1 11 5.5 Z" fill="{bg_color}"/>
      </g>
    </g>''')
    
    svg_parts.append('  </g>')
    svg_parts.append('</svg>')
    
    return '\n'.join(svg_parts)

def main():
    parser = argparse.ArgumentParser(description='Generate animated Pac-Man contribution graph')
    parser.add_argument('--user', required=True, help='GitHub username')
    parser.add_argument('--output', required=True, help='Output SVG file path')
    parser.add_argument('--theme', default='light', choices=['light', 'dark'], help='Theme (light or dark)')
    
    args = parser.parse_args()
    
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("Warning: GITHUB_TOKEN not set. API rate limits may apply.")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Fetch contributions
    print(f"Fetching contributions for {args.user}...")
    contributions = get_contributions(args.user, token)
    
    total = contributions['totalContributions']
    num_weeks = len(contributions['weeks'])
    print(f"Retrieved {total} total contributions across {num_weeks} weeks")
    
    # Generate SVG
    print(f"Generating SVG with {args.theme} theme...")
    svg = generate_svg(contributions, args.theme)
    
    # Write to file
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(svg)
    
    print(f"SVG saved to {args.output}")
    print(f"File size: {len(svg)} bytes")

if __name__ == '__main__':
    main()
