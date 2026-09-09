import {NextResponse} from 'next/server';
import {z} from 'zod';

const schema=z.object({type:z.string().min(1),project:z.string().min(1),model:z.string().min(1)});

export async function POST(request:Request){
  const parsed=schema.safeParse(await request.json().catch(()=>null));
  if(!parsed.success) return NextResponse.json({error:'Invalid engineering job payload',issues:parsed.error.issues},{status:400});
  const now=new Date().toISOString();
  return NextResponse.json({job:{id:`UEIP-${Date.now()}`,...parsed.data,state:'QUEUED',created_at:now,provenance:['demo-orchestrator'],evidence_state:'PROTOTYPE',message:'Queued only. No certified solver result has been generated.'}},{status:202});
}

export async function GET(){return NextResponse.json({service:'ARTEMIS UEIP job orchestrator',status:'operational',mode:'demo',solverExecution:false});}
