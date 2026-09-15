'use strict';

const Flow=require('./upgrade-program/creative-flow');

module.exports=Object.freeze({
  version:'1.0.0',
  summary:Flow.summary,
  catalog:Flow.catalog,
  discover:Flow.discover,
  compile:Flow.compile,
  execute:Flow.execute,
  run:Flow.run,
});
