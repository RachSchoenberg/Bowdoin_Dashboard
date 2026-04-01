// observablehq.config.js
export default {
  title: "Bowdoin Admissions Data Analysis",

  pages: [
    { name: "Executive Overview",   path: "/index"   },
    { name: "Bowdoin Deep Dive",    path: "/bowdoin" },
    { name: "Peer Comparison",      path: "/top20"   },
  ],

  
  toc: true,          // show in-page table of contents on the right
  pager: true,        // prev / next links at the bottom of each page

  theme: "dashboard", // matches the theme: dashboard in each .md front-matter
};