import { test } from 'node:test';
import assert from 'node:assert/strict';
import { classifyAdvisoryProvenance } from './audit-provenance.mjs';

const knownAudit = {
  vulnerabilities: {
    jest: {severity:'moderate',nodes:['node_modules/jest']},
    vulnerableRuntime: {severity:'high',nodes:['node_modules/runtime']},
  },
  metadata: {vulnerabilities: {moderate:1,high:1,total:2}},
};

test('distinguishes devOptional test tooling from potential runtime',()=>{
  const lock = {packages:{
    'node_modules/jest':{version:'30.5.2', devOptional:true},
    'node_modules/runtime':{version:'2.3.4'},
  }};
  const out=classifyAdvisoryProvenance(knownAudit,lock);
  assert.deepEqual(out.counts,{advisoryNames:2,devOrDevOptionalOnly:1,potentialRuntimeOrBuild:1,unverified:0});
  assert.equal(out.policy,'DIAGNOSTIC_ONLY_NOT_RELEASE_CLEARANCE');
});

test('unknown nodes are never silently treated as absent from the app',()=>{
  const out=classifyAdvisoryProvenance(knownAudit,{packages:{'node_modules/jest':{dev:true}}});
  assert.equal(out.counts.unverified,1);
});

test('mixed same-advisory node paths are classified as potential runtime',()=>{
  const out=classifyAdvisoryProvenance({vulnerabilities:{foo:{severity:'moderate',nodes:['node_modules/foo','node_modules/nested/node_modules/foo']}}},
    {packages:{'node_modules/foo':{dev:true},'node_modules/nested/node_modules/foo':{version:'1.0.0'}}});
  assert.equal(out.counts.potentialRuntimeOrBuild,1);
});

test('invalid or missing audit evidence fails closed',()=>{
  assert.throws(()=>classifyAdvisoryProvenance({vulnerabilities:{bad:{nodes:[]}}},{packages:{}}), /Missing affected nodes/);
  assert.throws(()=>classifyAdvisoryProvenance({},{}), /Valid npm audit JSON/);
  assert.throws(()=>classifyAdvisoryProvenance({vulnerabilities:{bad:{nodes:['../outside']}}},{packages:{}}), /Invalid affected path/);
});
