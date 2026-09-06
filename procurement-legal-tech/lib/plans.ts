export type Interval = "monthly" | "annual";
export type Plan = {id:string;name:string;monthly:number;annual:number;users:string;description:string;cta:string;featured?:boolean;features:string[]};
export const plans: Plan[] = [
 {id:"control",name:"Control",monthly:12,annual:120,users:"Up to 3 users",description:"For solo operators and very small teams.",cta:"Start free",features:["1 workspace","Vendor directory","Agreement and document register","Renewal-date tracking","Email reminders","Essential workflow templates","Basic dashboard","CSV import and export","Community/email support"]},
 {id:"oversight",name:"Oversight",monthly:39,annual:390,users:"Up to 15 users",description:"For teams that need clear ownership and repeatable approvals.",cta:"Start free",featured:true,features:["Everything in Control","Contract owner assignments","Vendor review workflows","Approval requests","Shared task tracking","Activity history","Renewal calendar","Team roles and permissions","Priority email support"]},
 {id:"command",name:"Command",monthly:99,annual:990,users:"Up to 50 users",description:"For operationally mature teams that need deeper visibility.",cta:"Talk to us",features:["Everything in Oversight","Advanced workflow automation","Custom fields and templates","Advanced reporting","Multi-workspace support","Audit log export","Priority onboarding session","Priority support"]}
];
export const addOns=[
 ["Guided Workspace Setup","CAD $79 one-time","We configure your workspace and install the essential templates."],
 ["Spreadsheet and Document Migration","from CAD $199 one-time","We help move existing vendor, agreement, and renewal data into your workspace."],
 ["Operations Template Library","CAD $15/month","Advanced templates for vendor onboarding, contract reviews, renewal governance, and purchasing approvals."],
 ["Priority Support","CAD $25/month","Faster support response and a monthly operational check-in."]
];
