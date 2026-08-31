import PublicAccessClient from "../../../components/PublicAccessClient";
import "./public-access.css";

type Props={params:Promise<{code:string}>};
export const metadata={title:"Три Короны · QR Access",description:"Безопасный QR-доступ Три Короны"};
export default async function PublicAccessPage({params}:Props){const {code}=await params;return <PublicAccessClient code={code}/>}
