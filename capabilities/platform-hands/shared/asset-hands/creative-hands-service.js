'use strict';
const U=require('./upgrade-program/foundation-utils');
const CoreHands=require('./upgrade-program/creative-hands');
const MeshHands=require('./upgrade-program/creative-mesh-hands');
const MeshEditHands=require('./upgrade-program/creative-mesh-edit-hands');
const MeshAdvancedHands=require('./upgrade-program/creative-mesh-advanced-hands');
const MeshModelingHands=require('./upgrade-program/creative-mesh-modeling-hands');
const AnimationHands=require('./upgrade-program/creative-animation-hands');
const MaterialProductionHands=require('./upgrade-program/creative-material-production-hands');
const Recipes=require('./upgrade-program/creative-recipes');
const registries=Object.freeze([CoreHands,MeshHands,MeshEditHands,MeshAdvancedHands,MeshModelingHands,AnimationHands,MaterialProductionHands]);
const recipeRegistries=Object.freeze([MeshHands,MeshEditHands,MeshAdvancedHands,MeshModelingHands,AnimationHands,MaterialProductionHands]);
function allHands(){return registries.flatMap((registry)=>registry.list());}
function owner(id){return registries.find((registry)=>registry.get(id));}
function get(id){const registry=owner(id);return registry?registry.get(id):null;}
function invoke(id,args){const registry=owner(id);if(!registry)throw new Error('unknown creative executable hand: '+id);return registry.invoke(id,args);}
function audit(){const parts=registries.map((registry)=>registry.audit()),by_family={};for(const part of parts)for(const [k,v] of Object.entries(part.by_family||{}))by_family[k]=(by_family[k]||0)+v;const ids=parts.flatMap((part)=>part.ids||[]),total=parts.reduce((sum,part)=>sum+part.total,0),value={schema:'axm.creative-executable-hand-audit/v1',version:'7.0.0',total,counts:{EXECUTABLE:total},by_family,ids,parts:parts.map((part)=>part.digest)};value.digest=U.sha256(value);return value;}
function recipeId(hand){return hand.id.replace(/^creative\./,'');}
function additionalRecipes(){return recipeRegistries.flatMap((registry)=>registry.list().map((hand)=>({id:recipeId(hand),state:'EXECUTABLE',primitives:[hand.id],truth:'Executed through a modular UC precision creative-hand registry.'})));}
function recipeRegistry(){const base=Recipes.registry(),extra=additionalRecipes(),value={schema:base.schema,version:'8.0.0',principle:base.principle,tools:base.tools.concat(extra),count:base.count+extra.length,executable_hands:audit().total};value.digest=U.sha256(value);return value;}
function invokeRecipe(id,args){for(const registry of recipeRegistries){const hand=registry.list().find((h)=>recipeId(h)===id);if(hand){const result=registry.invoke(hand.id,args),value={schema:'axm.creative-tool-recipe/v1',version:'8.0.0',tool_id:id,state:'EXECUTABLE',primitive:hand.id,result};value.digest=U.sha256(value);return value;}}return Recipes.invoke(id,args);}
module.exports=Object.freeze({version:'7.0.0',list:allHands,get,invoke,audit,recipeRegistry,invokeRecipe});