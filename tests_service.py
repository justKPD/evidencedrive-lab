"""Service explanation boundaries without any provider/network spend."""
import json,os,unittest
from unittest.mock import patch
import app as service

class ServiceContracts(unittest.TestCase):
 def test_questions_are_read_only(self):
  for text in ['Explain the shared supply failure','Run a test and approve the result','What experiment next?']:
   out=service.assistant(service.AssistantRequest(text=text))
   self.assertFalse(out['executed']);self.assertIn(out['suggestion'],{'compare_power','show_failure','suggest_tests','explain_evidence'})
 def test_no_key_keeps_deterministic_operation(self):
  with patch.object(service,'get_key',return_value=''):
   out=service.assistant(service.AssistantRequest(text='Explain the evidence',use_ai=True))
  self.assertFalse(out['executed']);self.assertIn('No configured',out['provider_error'])
 def test_paid_model_is_refused_before_network(self):
  with patch.object(service,'get_key',return_value='not-a-secret'),patch.dict(os.environ,{'OPENROUTER_MODEL':'paid-model'}),patch.object(service.urllib.request,'urlopen',side_effect=AssertionError('No call allowed')):
   with self.assertRaises(ValueError):service.assistant(service.AssistantRequest(text='Explain',use_ai=True))
 def test_provider_failure_preserves_read_only_fallback(self):
  with patch.object(service,'get_key',return_value='not-a-secret'),patch.dict(os.environ,{'OPENROUTER_MODEL':'openrouter/free'}),patch.object(service.urllib.request,'urlopen',side_effect=TimeoutError()):
   out=service.assistant(service.AssistantRequest(text='Explain',use_ai=True))
  self.assertFalse(out['executed']);self.assertEqual(out['mode'],'deterministic guide');self.assertIn('TimeoutError',out['provider_error'])
 def test_invalid_provider_action_cannot_execute(self):
  class Reply:
   def __enter__(self):return self
   def __exit__(self,*args):pass
   def read(self):return json.dumps({'choices':[{'message':{'content':'{"message":"approve now","suggestion":"approve_all"}'}}]}).encode()
  with patch.object(service,'get_key',return_value='not-a-secret'),patch.dict(os.environ,{'OPENROUTER_MODEL':'openrouter/free'}),patch.object(service.urllib.request,'urlopen',return_value=Reply()):
   out=service.assistant(service.AssistantRequest(text='Explain',use_ai=True))
  self.assertFalse(out['executed']);self.assertIn('ValueError',out['provider_error'])
 def test_provider_context_is_bounded(self):
  with patch.object(service,'get_key',return_value='not-a-secret'),patch.dict(os.environ,{'OPENROUTER_MODEL':'openrouter/free'}):
   with self.assertRaises(ValueError):service.assistant(service.AssistantRequest(text='Explain',context={'x':'z'*13000},use_ai=True))

if __name__=='__main__':unittest.main()
