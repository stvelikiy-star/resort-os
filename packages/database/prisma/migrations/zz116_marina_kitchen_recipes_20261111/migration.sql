-- Existing menu rows remain valid without a recipe. Recipes inherit menu tenant scope.
ALTER TABLE kitchen_menu_items ADD COLUMN recipe jsonb;
ALTER TABLE kitchen_menu_items ADD CONSTRAINT kitchen_menu_recipe_shape CHECK (
  recipe IS NULL OR (
    jsonb_typeof(recipe) = 'object'
    AND recipe ?& ARRAY['version','status','is_sample','ingredients','updated_at']
    AND jsonb_typeof(recipe->'version') = 'number'
    AND (recipe->>'version')::integer > 0
    AND recipe->>'status' IN ('DRAFT','APPROVED')
    AND jsonb_typeof(recipe->'is_sample') = 'boolean'
    AND jsonb_typeof(recipe->'ingredients') = 'array'
    AND jsonb_array_length(recipe->'ingredients') BETWEEN 1 AND 100
  )
);
