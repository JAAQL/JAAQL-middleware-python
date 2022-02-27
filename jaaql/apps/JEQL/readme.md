# Local Development
JEQL uses es6 (a 'flavour' of Javascript supported by all modern browsers) that allows for modules. Browsers will perform a CORS check before loading the 
module in. If you are developing locally then this CORS check will fail. The easiest way around this is to use firefox, head to the about:config page and then 
type in privacy.file_unique_origin and set it to false. Also set security.fileuri.strict_origin_policy to false. This will make your browser insecure so please 
do not use firefox for everyday browsing after this