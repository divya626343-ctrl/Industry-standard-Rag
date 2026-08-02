import type { CSSProperties } from "react";

interface IconProps {
  size?: number;
  style?: CSSProperties;
  className?: string;
}

/* ---------------------------------------------------------------------
 * Icons below this line are your provided SVGs, paths unchanged.
 * ------------------------------------------------------------------- */

// pajamas_duo-chat-new.svg — "New chat"
export function NewChatIcon({ size = 16, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <path fillRule="evenodd" clipRule="evenodd" d="M1.5 4C1.5 3.60218 1.65804 3.22064 1.93934 2.93934C2.22064 2.65804 2.60218 2.5 3 2.5H13C13.3978 2.5 13.7794 2.65804 14.0607 2.93934C14.342 3.22064 14.5 3.60218 14.5 4V7.25C14.5 7.44891 14.579 7.63968 14.7197 7.78033C14.8603 7.92098 15.0511 8 15.25 8C15.4489 8 15.6397 7.92098 15.7803 7.78033C15.921 7.63968 16 7.44891 16 7.25V4C16 3.20435 15.6839 2.44129 15.1213 1.87868C14.5587 1.31607 13.7956 1 13 1H3C2.20435 1 1.44129 1.31607 0.87868 1.87868C0.31607 2.44129 0 3.20435 0 4L0 15.25C0.000130387 15.3982 0.0441878 15.5431 0.126608 15.6663C0.209028 15.7895 0.326113 15.8856 0.463076 15.9423C0.60004 15.999 0.750737 16.0138 0.896136 15.985C1.04154 15.9561 1.17511 15.8848 1.28 15.78L4.063 13H8.25C8.44891 13 8.63968 12.921 8.78033 12.7803C8.92098 12.6397 9 12.4489 9 12.25C9 12.0511 8.92098 11.8603 8.78033 11.7197C8.63968 11.579 8.44891 11.5 8.25 11.5H3.443L3.223 11.72L1.5 13.44V4ZM13 14C12.8011 14 12.6103 13.921 12.4697 13.7803C12.329 13.6397 12.25 13.4489 12.25 13.25V11.75H10.75C10.5511 11.75 10.3603 11.671 10.2197 11.5303C10.079 11.3897 10 11.1989 10 11C10 10.8011 10.079 10.6103 10.2197 10.4697C10.3603 10.329 10.5511 10.25 10.75 10.25H12.25V8.75C12.25 8.55109 12.329 8.36032 12.4697 8.21967C12.6103 8.07902 12.8011 8 13 8C13.1989 8 13.3897 8.07902 13.5303 8.21967C13.671 8.36032 13.75 8.55109 13.75 8.75V10.25H15.25C15.4489 10.25 15.6397 10.329 15.7803 10.4697C15.921 10.6103 16 10.8011 16 11C16 11.1989 15.921 11.3897 15.7803 11.5303C15.6397 11.671 15.4489 11.75 15.25 11.75H13.75V13.25C13.75 13.4489 13.671 13.6397 13.5303 13.7803C13.3897 13.921 13.1989 14 13 14Z" fill="black"/>
    </svg>
  );
}

// typcn_arrow-up.svg — send button (self-contained w/ gray bg + white arrow)
export function SendButtonIcon({ size = 24, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <rect width="24" height="24" rx="4" fill="#B0B0B0"/>
      <path d="M12 5.79297L7.29297 10.5C7.20013 10.5928 7.12648 10.703 7.07623 10.8243C7.02598 10.9457 7.00012 11.0757 7.00012 11.207C7.00012 11.3383 7.02598 11.4683 7.07623 11.5896C7.12648 11.7109 7.20013 11.8211 7.29297 11.914C7.38582 12.0068 7.49604 12.0805 7.61735 12.1307C7.73865 12.181 7.86867 12.2068 7.99997 12.2068C8.13127 12.2068 8.26129 12.181 8.3826 12.1307C8.5039 12.0805 8.61413 12.0068 8.70697 11.914L11 9.62097V17.207C11 17.4722 11.1053 17.7265 11.2929 17.9141C11.4804 18.1016 11.7348 18.207 12 18.207C12.2652 18.207 12.5195 18.1016 12.7071 17.9141C12.8946 17.7265 13 17.4722 13 17.207V9.62097L15.293 11.914C15.3856 12.0072 15.4958 12.0811 15.6171 12.1316C15.7385 12.182 15.8686 12.208 16 12.208C16.1314 12.208 16.2615 12.182 16.3828 12.1316C16.5042 12.0811 16.6143 12.0072 16.707 11.914C16.8944 11.7264 16.9998 11.4721 16.9998 11.207C16.9998 10.9418 16.8944 10.6875 16.707 10.5L12 5.79297Z" fill="#FFF6F6"/>
    </svg>
  );
}

// typcn_arrow-up (1).svg — bare white arrow, used inside the gold Upload button
export function BareArrowUpIcon({ size = 20, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <path d="M12.0001 2L4.46858 9.58337C4.32002 9.73295 4.20218 9.91053 4.12178 10.106C4.04138 10.3014 4 10.5109 4 10.7224C4 10.9339 4.04138 11.1434 4.12178 11.3389C4.20218 11.5343 4.32002 11.7119 4.46858 11.8614C4.61713 12.011 4.7935 12.1297 4.98759 12.2106C5.18169 12.2916 5.38973 12.3333 5.59982 12.3333C5.80991 12.3333 6.01794 12.2916 6.21204 12.2106C6.40614 12.1297 6.5825 12.011 6.73106 11.8614L10.4 8.16723V20.3889C10.4 20.8162 10.5686 21.226 10.8686 21.5281C11.1687 21.8303 11.5757 22 12.0001 22C12.4244 22 12.8314 21.8303 13.1315 21.5281C13.4315 21.226 13.6001 20.8162 13.6001 20.3889V8.16723L17.269 11.8614C17.4173 12.0116 17.5936 12.1307 17.7877 12.212C17.9818 12.2933 18.19 12.3352 18.4003 12.3352C18.6105 12.3352 18.8187 12.2933 19.0129 12.212C19.207 12.1307 19.3833 12.0116 19.5315 11.8614C19.8315 11.5593 20 11.1496 20 10.7224C20 10.2952 19.8315 9.8855 19.5315 9.58337L12.0001 2Z" fill="white"/>
    </svg>
  );
}

// material-symbols_delete-outline-rounded.svg — document delete
export function DeleteIcon({ size = 28, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <rect width="28" height="28" rx="5" fill="#FFD7D8"/>
      <path d="M9 23C8.45 23 7.97934 22.8043 7.588 22.413C7.19667 22.0217 7.00067 21.5507 7 21V8C6.71667 8 6.47934 7.904 6.288 7.712C6.09667 7.52 6.00067 7.28267 6 7C5.99934 6.71733 6.09534 6.48 6.288 6.288C6.48067 6.096 6.718 6 7 6H11C11 5.71667 11.096 5.47933 11.288 5.288C11.48 5.09667 11.7173 5.00067 12 5H16C16.2833 5 16.521 5.096 16.713 5.288C16.905 5.48 17.0007 5.71733 17 6H21C21.2833 6 21.521 6.096 21.713 6.288C21.905 6.48 22.0007 6.71733 22 7C21.9993 7.28267 21.9033 7.52033 21.712 7.713C21.5207 7.90567 21.2833 8.00133 21 8V21C21 21.55 20.8043 22.021 20.413 22.413C20.0217 22.805 19.5507 23.0007 19 23H9ZM19 8H9V21H19V8ZM12.713 18.713C12.9043 18.521 13 18.2833 13 18V11C13 10.7167 12.904 10.4793 12.712 10.288C12.52 10.0967 12.2827 10.0007 12 10C11.7173 9.99933 11.48 10.0953 11.288 10.288C11.096 10.4807 11 10.718 11 11V18C11 18.2833 11.096 18.521 11.288 18.713C11.48 18.905 11.7173 19.0007 12 19C12.2827 18.9993 12.5203 18.9043 12.713 18.713ZM16.713 18.712C16.9043 18.5213 17 18.284 17 18V11C17 10.7167 16.904 10.4793 16.712 10.288C16.52 10.0967 16.2827 10.0007 16 10C15.7173 9.99933 15.48 10.0953 15.288 10.288C15.096 10.4807 15 10.718 15 11V18C15 18.2833 15.096 18.521 15.288 18.713C15.48 18.905 15.7173 19.0007 16 19C16.2827 18.9993 16.5203 18.9033 16.713 18.712Z" fill="#730002"/>
    </svg>
  );
}

// gridicons_dropdown.svg — chevron for dropdown / trace expand (rotate 180 via style for "up")
export function DropdownChevronIcon({ size = 24, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <path d="M7 10L12 15L17 10H7Z" fill="black"/>
    </svg>
  );
}

// Icon_Right.svg — circular chevron, used for pagination (rotate 180 via style for "previous")
export function CircleChevronIcon({ size = 32, style, className }: IconProps) {
  return (
    <svg width={size} height={(size * 28) / 32} viewBox="0 0 32 28" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <rect x="0.5" y="0.5" width="31" height="27" rx="7.5" stroke="#B0B0B0"/>
      <path d="M13.5 20.6666L20.1667 13.9999L13.5 7.33325" stroke="#454545" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// tabler_layout-sidebar-right-collapse-filled.svg — documents panel toggle
export function DocumentsPanelToggleIcon({ size = 40, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 55 55" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <g filter="url(#toggle-shadow)">
        <rect x="7.3999" y="4.40002" width="40" height="40" rx="9" fill="#8A5F1B" shapeRendering="crispEdges"/>
        <path d="M35.3999 12.4C36.4202 12.4 37.4019 12.7898 38.1442 13.4897C38.8866 14.1897 39.3334 15.1468 39.3932 16.1654L39.3999 16.4V32.4C39.4 33.4203 39.0101 34.402 38.3102 35.1444C37.6102 35.8867 36.6531 36.3335 35.6346 36.3934L35.3999 36.4H19.3999C18.3796 36.4001 17.3979 36.0103 16.6556 35.3103C15.9132 34.6104 15.4664 33.6532 15.4066 32.6347L15.3999 32.4V16.4C15.3998 15.3797 15.7897 14.398 16.4896 13.6557C17.1896 12.9133 18.1467 12.4665 19.1652 12.4067L19.3999 12.4H35.3999ZM31.3999 15.0667H19.3999C19.0733 15.0667 18.7581 15.1866 18.5141 15.4036C18.27 15.6207 18.1141 15.9197 18.0759 16.244L18.0666 16.4V32.4C18.0666 32.7266 18.1865 33.0418 18.4035 33.2859C18.6205 33.5299 18.9196 33.6858 19.2439 33.724L19.3999 33.7334H31.3999V15.0667ZM24.2172 20.68L24.3426 20.7907L27.0092 23.4574C27.2388 23.6869 27.3767 23.9924 27.3971 24.3164C27.4175 24.6405 27.3189 24.9608 27.1199 25.2174L27.0092 25.3427L24.3426 28.0094C24.1026 28.2485 23.7807 28.3873 23.4421 28.3977C23.1035 28.408 22.7736 28.2891 22.5195 28.065C22.2654 27.841 22.1062 27.5286 22.074 27.1914C22.0419 26.8542 22.1394 26.5173 22.3466 26.2494L22.4572 26.124L24.1799 24.4L22.4572 22.676C22.2277 22.4464 22.0898 22.141 22.0694 21.8169C22.049 21.4929 22.1476 21.1726 22.3466 20.916L22.4572 20.7907C22.6868 20.5611 22.9923 20.4232 23.3163 20.4028C23.6404 20.3825 23.9607 20.481 24.2172 20.68Z" fill="white"/>
      </g>
      <defs>
        <filter id="toggle-shadow" x="-0.0001" y="0.0000243" width="54.8" height="54.8" filterUnits="userSpaceOnUse" colorInterpolationFilters="sRGB">
          <feFlood floodOpacity="0" result="BackgroundImageFix"/>
          <feColorMatrix in="SourceAlpha" type="matrix" values="0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 127 0" result="hardAlpha"/>
          <feOffset dy="3"/>
          <feGaussianBlur stdDeviation="3.7"/>
          <feComposite in2="hardAlpha" operator="out"/>
          <feColorMatrix type="matrix" values="0 0 0 0 0.3125 0 0 0 0 0.309796 0 0 0 0 0.309796 0 0 0 0.25 0"/>
          <feBlend mode="normal" in2="BackgroundImageFix" result="effect1_dropShadow"/>
          <feBlend mode="normal" in="SourceGraphic" in2="effect1_dropShadow" result="shape"/>
        </filter>
      </defs>
    </svg>
  );
}

// Rectangle_1.svg — small status/alert dot
export function AlertDot({ size = 8, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 8 8" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <rect width="8" height="8" rx="4" fill="#FF383C"/>
    </svg>
  );
}

/* ---------------------------------------------------------------------
 * Icons below this line were NOT in your provided set — added to cover
 * gaps (close panel, locked-strategy badge, guardrail/error states).
 * Styled to match the stroke weight/rounding of Icon_Right so they don't
 * look out of place; swap these out freely if you have real assets.
 * ------------------------------------------------------------------- */

export function CloseIcon({ size = 18, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 18 18" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <path d="M4 4L14 14M14 4L4 14" stroke="#454545" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

export function LockIcon({ size = 14, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <rect x="3" y="6.2" width="8" height="6" rx="1.4" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M4.6 6.2V4.4C4.6 3.07452 5.67452 2 7 2C8.32548 2 9.4 3.07452 9.4 4.4V6.2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
    </svg>
  );
}

export function AlertTriangleIcon({ size = 16, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <path d="M8 2.2L14.5 13.5H1.5L8 2.2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round"/>
      <path d="M8 6.5V9.3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <circle cx="8" cy="11.4" r="0.9" fill="currentColor"/>
    </svg>
  );
}

export function AlertCircleIcon({ size = 16, style, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="none" style={style} className={className} xmlns="http://www.w3.org/2000/svg">
      <circle cx="8" cy="8" r="6.3" stroke="currentColor" strokeWidth="1.3"/>
      <path d="M8 5V8.6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/>
      <circle cx="8" cy="11" r="0.9" fill="currentColor"/>
    </svg>
  );
}
