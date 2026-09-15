'use strict';
const Hands=require('./upgrade-program/creative-hands');
const Recipes=require('./upgrade-program/creative-recipes');
module.exports=Object.freeze({
  version:'1.0.0',
  list:Hands.list,
  get:Hands.get,
  invoke:Hands.invoke,
  audit:Hands.audit,
  recipeRegistry:Recipes.registry,
  invokeRecipe:Recipes.invoke,
});
