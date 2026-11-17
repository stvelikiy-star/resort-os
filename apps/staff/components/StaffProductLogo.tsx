/** The approved platform mark, separate from any property's own identity. */
export default function StaffProductLogo({size = 48}: {size?: number}) {
  return <img src="/marina-smart-approved.png" alt="MARINA SMART" width={size} height={size}
    style={{width:size,height:size,objectFit:'contain',flexShrink:0,display:'block'}}/>;
}
