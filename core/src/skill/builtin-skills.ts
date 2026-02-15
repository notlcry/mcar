/**
 * Built-in skill definitions for mcar.
 *
 * These are registered automatically at startup.
 */

import type { SkillDefinition } from "./types.js";

/**
 * Self-check skill: reads all sensors and reports status.
 */
export const SKILL_SELF_CHECK: SkillDefinition = {
  skill_id: "skill.self_check",
  name: "Self Check",
  description: "Run a comprehensive self-check: read sensors, check obstacles, report status.",
  version: "1.0.0",
  risk_level: "READ_ONLY",
  steps: [
    {
      id: "ultrasonic",
      capability_id: "tool.sensor.ultrasonic",
      params: {},
      on_error: "skip",
    },
    {
      id: "infrared",
      capability_id: "tool.sensor.infrared",
      params: {},
      on_error: "skip",
    },
  ],
};

/**
 * Night mode skill: mute sound + show sleeping expression.
 */
export const SKILL_NIGHT_MODE: SkillDefinition = {
  skill_id: "skill.night_mode",
  name: "Night Mode",
  description: "Enter night mode: mute audio output and show sleeping expression.",
  version: "1.0.0",
  risk_level: "NORMAL",
  steps: [
    {
      id: "show_sleeping",
      capability_id: "tool.display.show_expression",
      params: { expression: "sleeping" },
      on_error: "skip",
    },
    {
      id: "announce",
      capability_id: "tool.voice.synthesize",
      params: { text: "Entering night mode. Good night!", voice: "zh-CN-XiaoxiaoNeural" },
      on_error: "skip",
    },
  ],
};

/**
 * Patrol skill: move forward, check sensors, turn, repeat.
 */
export const SKILL_PATROL: SkillDefinition = {
  skill_id: "skill.patrol",
  name: "Patrol",
  description: "Simple patrol: move forward, check for obstacles, turn if blocked. Parameterize with speed and duration.",
  version: "1.0.0",
  risk_level: "DANGEROUS",
  parameters: {
    speed: { type: "integer", description: "Movement speed (10-100)", default: 30 },
    cycles: { type: "integer", description: "Number of patrol cycles", default: 2 },
  },
  steps: [
    {
      id: "check_obstacle",
      capability_id: "tool.sensor.infrared",
      params: {},
      on_error: "abort",
    },
    {
      id: "move_forward",
      capability_id: "tool.motion.forward",
      params: { speed: "${speed}", duration_ms: 1500 },
      condition: {
        type: "previous_result",
        path: "check_obstacle.left_obstacle",
        op: "==",
        value: false,
      },
      on_error: "skip",
    },
    {
      id: "check_after_move",
      capability_id: "tool.sensor.ultrasonic",
      params: {},
      on_error: "skip",
    },
    {
      id: "turn",
      capability_id: "tool.motion.turn_right",
      params: { speed: "${speed}", duration_ms: 800 },
      on_error: "skip",
    },
  ],
};

/**
 * All built-in skills.
 */
export const BUILTIN_SKILLS: readonly SkillDefinition[] = [
  SKILL_SELF_CHECK,
  SKILL_NIGHT_MODE,
  SKILL_PATROL,
];
