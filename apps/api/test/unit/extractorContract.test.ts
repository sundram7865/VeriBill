import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { z } from 'zod';
import { extractMetadataSchema, extractResponseSchema } from '../../src/extractor/extractorSchemas';

/**
 * Contract test: the Zod mirror must describe the same shape as the Pydantic models. Both are
 * reduced to a canonical "shape" (property names, required keys, types, enums, nullability),
 * ignoring cosmetic differences such as titles, descriptions and $ref placement.
 */
type Json = Record<string, any>;

const CONTRACT_DIR = path.resolve(__dirname, '../../../../services/extractor/contract');

function load(name: string): Json {
  return JSON.parse(readFileSync(path.join(CONTRACT_DIR, name), 'utf8'));
}

function resolve(schema: Json, root: Json): Json {
  if (schema.$ref) {
    const name = String(schema.$ref).split('/').at(-1) as string;
    return resolve(root.$defs?.[name] ?? root.definitions?.[name], root);
  }
  return schema;
}

function shape(input: Json, root: Json): unknown {
  const schema = resolve(input, root);
  const variants = schema.anyOf ?? schema.oneOf;
  if (variants) {
    const parts = variants.map((v: Json) => shape(v, root));
    return { anyOf: parts.map((p: unknown) => JSON.stringify(p)).sort() };
  }
  if (Array.isArray(schema.type)) {
    // Zod writes nullable as type: ["string", "null"]; Pydantic writes the same as anyOf.
    return { anyOf: schema.type.map((t: string) => JSON.stringify(t)).sort() };
  }
  if (schema.enum) return { enum: [...schema.enum].sort() };
  if (schema.const !== undefined) return { enum: [schema.const] };
  if (schema.type === 'array') return { array: shape(schema.items ?? {}, root) };
  if (schema.type === 'object' || schema.properties) {
    if (!schema.properties) {
      return { record: shape(schema.additionalProperties ?? {}, root) };
    }
    const props: Record<string, unknown> = {};
    for (const key of Object.keys(schema.properties).sort()) {
      props[key] = shape(schema.properties[key], root);
    }
    return { object: props, required: [...(schema.required ?? [])].sort() };
  }
  return schema.type ?? 'any';
}

function zodShape(schema: z.ZodType, io: 'input' | 'output'): unknown {
  const json = z.toJSONSchema(schema, { io, unrepresentable: 'any' }) as Json;
  return shape(json, json);
}

describe('extractor contract (Pydantic <-> Zod)', () => {
  it('response shapes match', () => {
    const pydantic = load('extract_response.schema.json');
    expect(zodShape(extractResponseSchema, 'output')).toEqual(shape(pydantic, pydantic));
  });

  it('metadata shapes match', () => {
    const pydantic = load('extract_metadata.schema.json');
    expect(zodShape(extractMetadataSchema, 'input')).toEqual(shape(pydantic, pydantic));
  });
});
