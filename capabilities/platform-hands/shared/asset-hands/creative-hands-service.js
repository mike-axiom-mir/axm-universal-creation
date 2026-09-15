'use strict';
const U=require('./upgrade-program/foundation-utils');
const Hands=require('./upgrade-program/creative-hands');
const MeshHands=require('./upgrade-program/creative-mesh-hands');
const Recipes=require('./upgrade-program/creative-recipes');
function allHands(){return Hands.list().concat(MeshHands.list());}
function get(id){return Hands.get(id)||MeshHands.get(id);}
function invoke(id,args){return MeshHands.get(id)?MeshHands.invoke(id,args):Hands.invoke(id,args);}
function audit(){const a=Hands.audit(),m=MeshHands.audit(),by_family=Object.assign({},a.by_family);Object.entries(m.by_family).forEach(([k,v])=>{by_family[k]=(by_family[k]||0)+v;});const value={schema:'axm.creative-executable-hand-audit/v1',version:'2.0.0',total:a.total+m.total,counts:{EXECUTABLE:a.total+m.total},by_family,ids:a.ids.concat(m.ids),parts:{creative:a.digest,mesh:m.digest}};value.digest=U.sha256(value);return value;}
function meshRecipeId(hand){return hand.id.replace(/^creative\./,'');}
function recipeRegistry(){const base=Recipes.registry(),mesh=MeshHands.list().map((hand)=>({id:meshRecipeId(hand),state:'EXECUTABLE',primitives:[hand.id],truth:'Executed through the UC precision-mesh hand registry.'}));const value={schema:base.schema,version:'3.0.0',principle:base.principle,tools:base.tools.concat(mesh),count:base.count+mesh.length,executable_hands:audit().total};value.digest=U.sha256(value);return value;}
function invokeRecipe(id,args){const hand=MeshHands.list().find((h)=>meshRecipeId(h)===id);if(!hand)return Recipes.invoke(id,args);const result=MeshHands.invoke(hand.id,args);const value={schema:'axm.creative-tool-recipe/v1',version:'3.0.0',tool_id:id,state:'EXECUTABLE',primitive:hand.id,result};value.digest=U.sha256(value);return value;}
module.exports=Object.freeze({version:'2.0.0',list:allHands,get,invoke,audit,recipeRegistry,invokeRecipe});