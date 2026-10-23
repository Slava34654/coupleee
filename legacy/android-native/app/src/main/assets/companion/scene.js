/* Original procedural characters. All meshes and animation run offline. */
(() => {
  const report = message => { if (window.Companion) Companion.error(String(message)); document.getElementById('error').style.display='block'; };
  window.addEventListener('error', e => report(e.message));
  try {
    const T = THREE;
    const renderer = new T.WebGLRenderer({antialias:true, alpha:false, powerPreference:'low-power'});
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.6));
    renderer.shadowMap.enabled = true; renderer.shadowMap.type = T.PCFSoftShadowMap;
    renderer.outputColorSpace = T.SRGBColorSpace;
    document.body.prepend(renderer.domElement);
    renderer.domElement.addEventListener('webglcontextlost', e => { e.preventDefault(); report('WebGL context lost'); });
    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(34, 1, .1, 60);
    camera.position.set(0, 2.75, 7.9); camera.lookAt(0, 1.05, 0);
    scene.add(new T.HemisphereLight(0xfff8ee, 0xb79ba9, 2.1));
    const sun = new T.DirectionalLight(0xfff4df, 3.1); sun.position.set(-3, 6, 5); sun.castShadow=true;
    sun.shadow.mapSize.set(1024,1024); sun.shadow.camera.left=-4; sun.shadow.camera.right=4;
    sun.shadow.camera.top=5; sun.shadow.camera.bottom=-3; sun.shadow.normalBias=.025; scene.add(sun);
    const fill=new T.DirectionalLight(0xe5dcff,1); fill.position.set(4,2,-2); scene.add(fill);
    const mat = (color, roughness=.74) => new T.MeshStandardMaterial({color,roughness});
    const cream=mat(0xf4cda6), creamLight=mat(0xffead2), pink=mat(0xe8a2b7), dark=mat(0x493746),
      white=mat(0xfffaf1), skin=mat(0xf1bd9f), blue=mat(0x6eaaa7), iris=mat(0x5b8e83,.3);
    const sphere=new T.SphereGeometry(1,32,24);
    function ball(parent,m,x,y,z,sx,sy=sx,sz=sx) {
      const o=new T.Mesh(sphere,m); o.position.set(x,y,z); o.scale.set(sx,sy,sz); o.castShadow=true; o.receiveShadow=true; parent.add(o); return o;
    }
    function box(parent,m,x,y,z,sx,sy,sz) {
      const o=new T.Mesh(new T.BoxGeometry(sx,sy,sz),m); o.position.set(x,y,z); o.castShadow=true; o.receiveShadow=true; parent.add(o); return o;
    }
    function tube(parent,m,points,radius) {
      const curve=new T.CatmullRomCurve3(points.map(p=>new T.Vector3(...p)));
      const o=new T.Mesh(new T.TubeGeometry(curve,24,radius,8,false),m); parent.add(o); o.castShadow=true; return o;
    }
    function cylinder(parent,m,x,y,z,rt,rb,h) {
      const o=new T.Mesh(new T.CylinderGeometry(rt,rb,h,48),m); o.position.set(x,y,z); parent.add(o); o.receiveShadow=true; o.castShadow=true; return o;
    }
    const room = new T.Group(); scene.add(room);
    const floorMat=mat(0xefdad8), wallMat=mat(0xf8e6e4), rugMat=mat(0xe5b9c6);
    cylinder(room,floorMat,0,-.15,0,3.6,3.6,.24);
    cylinder(room,rugMat,0,.003,0,1.7,1.7,.04);
    cylinder(room,mat(0xf1d2d8),0,.026,0,1.46,1.46,.015);
    const arch = new T.Shape(); arch.moveTo(-3,-.15); arch.lineTo(-3,2.5); arch.quadraticCurveTo(-3,4,0,4);
    arch.quadraticCurveTo(3,4,3,2.5); arch.lineTo(3,-.15); arch.closePath();
    const wall=new T.Mesh(new T.ShapeGeometry(arch),wallMat); wall.position.z=-1.9; wall.receiveShadow=true; room.add(wall);
    // A softly lit window, a planter and a low toy shelf frame the character.
    const windowFrame=mat(0xfff3e7), glass=mat(0xe8d4ba);
    box(room,windowFrame,-1.55,2.17,-1.79,1.25,1.75,.13);
    box(room,glass,-1.55,2.17,-1.7,1.07,1.57,.03);
    box(room,windowFrame,-1.55,2.17,-1.65,.055,1.6,.06);
    box(room,windowFrame,-1.55,2.17,-1.65,1.1,.055,.06);
    const leaf=mat(0x819e85);
    cylinder(room,mat(0xd7a391),-2.1,.35,-.35,.24,.19,.57);
    for(let i=0;i<5;i++) {
      const a=i*1.25; const x=-2.1+Math.cos(a)*.16,z=-.35+Math.sin(a)*.15;
      tube(room,leaf,[[-2.1,.55,-.35],[x,.87,z],[x,1.2+(i%2)*.15,z]],.025);
      const l=ball(room,leaf,x,1.13+(i%2)*.15,z,.14,.31,.07); l.rotation.z=Math.cos(a)*.6;
    }
    box(room,mat(0xd7b29f),1.9,.38,-.95,1.1,.12,.65);
    for (const x of [1.5,2.3]) box(room,mat(0xd7b29f),x,.19,-.95,.10,.38,.48);
    ball(room,pink,1.64,.63,-.95,.19); box(room,blue,2.08,.59,-.95,.29,.31,.28);
    const starMat=mat(0xf6cd76);
    for(let i=0;i<3;i++) ball(room,starMat,.4+i*.4,2.8-(i%2)*.22,-1.7,.07);
    const root=new T.Group(); scene.add(root);
    let head,eyes=[],arms=[],tail,hatGroup,dirt=[];
    let state={type:'PET',room:'rose',energy:.8,joy:.8,hunger:.8,clean:.8,level:1,sleeping:false,accessory:'none'};
    function clear(g) { while(g.children.length) g.remove(g.children[0]); }
    function eye(parent,x,y,z,baby) {
      const g=new T.Group(); g.position.set(x,y,z); parent.add(g);
      ball(g,dark,0,0,0,baby?.09:.105,.13,.045);
      ball(g,iris,0,-.015,.031,.068,.084,.017);
      ball(g,dark,0,.005,.047,.037,.072,.01);
      ball(g,white,-.027,.052,.060,.024); ball(g,white,.025,-.035,.06,.011);
      eyes.push(g);
    }
    function buildCharacter() {
      clear(root); eyes=[]; arms=[]; tail=null; dirt=[];
      const baby=state.type==='BABY';
      ball(root,baby?blue:cream,0,.76,0,.55,.67,.40);
      ball(root,baby?mat(0xacc9bd):creamLight,0,.78,.345,.32,.4,.08);
      for(const side of [-1,1]) {
        ball(root,baby?white:creamLight,side*.32,.18,.22,.26,.18,.34);
        const arm=new T.Group(); arm.position.set(side*.45,1,0); root.add(arm);
        ball(arm,baby?blue:cream,side*.06,-.19,.07,.16,.34,.17);
        ball(arm,baby?skin:creamLight,side*.07,-.39,.10,.15,.15,.15); arms.push(arm);
      }
      head=new T.Group(); head.position.set(0,1.65,.06); root.add(head);
      ball(head,baby?skin:cream,0,0,0,.68,.60,.53);
      if(baby) {
        for(const side of [-1,1]) ball(head,skin,side*.66,-.05,0,.13,.19,.12);
        const hair=mat(0x77513e);
        tube(head,hair,[[-.17,.54,.06],[-.12,.68,.02],[.06,.71,.06],[.16,.62,.16]],.075);
        ball(head,skin,0,-.13,.53,.075,.07,.07);
        ball(head,pink,0,-.31,.49,.14,.085,.04);
        const ring=new T.Mesh(new T.TorusGeometry(.082,.025,10,28),blue); ring.position.set(0,-.33,.57); head.add(ring);
      } else {
        for(const side of [-1,1]) {
          const ear=new T.Mesh(new T.ConeGeometry(.24,.55,3),cream); ear.position.set(side*.46,.46,-.02);
          ear.rotation.z=-side*.20; ear.rotation.y=Math.PI; head.add(ear);
          const inner=new T.Mesh(new T.ConeGeometry(.13,.32,3),pink); inner.position.set(side*.46,.48,.115);
          inner.rotation.z=-side*.20; inner.rotation.y=Math.PI; head.add(inner);
          ball(head,creamLight,side*.13,-.21,.45,.21,.16,.12);
          for(let i=0;i<3;i++) tube(head,mat(0xbfa18d),[[side*.25,-.22,.53],[side*.57,-.18-i*.045,.51]],.008);
        }
        ball(head,pink,0,-.12,.575,.085,.055,.035);
        tube(head,dark,[[0,-.18,.56],[0,-.24,.57],[.09,-.27,.54]],.012);
        tail=new T.Group(); root.add(tail);
        tube(tail,cream,[[.4,.35,-.19],[.84,.48,-.35],[.97,.85,-.28],[.84,1.03,-.25]],.12);
        ball(tail,creamLight,.84,1.03,-.25,.125);
      }
      for(const side of [-1,1]) {
        eye(head,side*.25,baby?.03:.04,.478,baby);
        ball(head,pink,side*.43,-.17,.426,.115,.056,.032);
      }
      hatGroup=new T.Group(); head.add(hatGroup); setHat();
      const dirtMat=mat(0xab927b);
      for(let i=0;i<3;i++) dirt.push(ball(root,dirtMat,(i-1)*.17,.64+(i%2)*.14,.425,.055,.033,.008));
    }
    function setHat() {
      clear(hatGroup);
      if(state.accessory==='bow') {
        for(const side of [-1,1]) { const b=ball(hatGroup,pink,side*.12,.55,.4,.16,.11,.07); b.rotation.z=side*.35; }
        ball(hatGroup,white,0,.55,.43,.06);
      }
      if(state.accessory==='crown') {
        cylinder(hatGroup,starMat,0,.64,.08,.30,.25,.16);
        for(let i=0;i<5;i++) {
          const a=i*Math.PI*2/5;
          const spike=new T.Mesh(new T.ConeGeometry(.085,.25,4),starMat);
          spike.position.set(Math.cos(a)*.23,.82,.08+Math.sin(a)*.23); hatGroup.add(spike);
          ball(hatGroup,pink,Math.cos(a)*.23,.94,.08+Math.sin(a)*.23,.035);
        }
      }
    }
    buildCharacter();
    const props=new T.Group(); scene.add(props);
    const bowl=cylinder(props,pink,0,.16,1,.36,.25,.17);
    const meal=cylinder(props,mat(0xbb895c),0,.25,1,.29,.29,.035);
    const toy=ball(props,blue,.9,.2,.8,.2);
    bowl.visible=meal.visible=toy.visible=false;
    const particles=[]; const particleGroup=new T.Group(); scene.add(particleGroup);
    for(let i=0;i<16;i++) {
      const p=ball(particleGroup,i%2?pink:white,0,0,0,.045+(i%3)*.018);
      particles.push(p); p.visible=false;
    }
    const palettes={rose:[0xf5e6e5,0xf8e6e4,0xe5b9c6],garden:[0xe5efe7,0xe5efe3,0xaac8b4],night:[0x39394f,0x4c4762,0x9b8eaf],beach:[0xf3e5cf,0xe2eeee,0xd9c296]};
    let animation='idle',actionStart=0,eventId=0,targetYaw=0,yaw=0;
    window.setCompanion = next => {
      const old=state; state=next;
      if(old.type!==state.type) buildCharacter();
      if(old.accessory!==state.accessory) setHat();
      const p=palettes[state.room]||palettes.rose;
      scene.background=new T.Color(p[0]); wallMat.color.setHex(p[1]); rugMat.color.setHex(p[2]);
      document.body.style.background='#'+p[0].toString(16);
      if(next.eventId!==eventId) { eventId=next.eventId; animation=next.animation||'idle'; actionStart=performance.now()/1000; }
    };
    window.setCompanion(state);
    const pointer={x:0,y:0,drag:false};
    renderer.domElement.addEventListener('pointerdown',e=>{pointer.x=e.clientX;pointer.y=e.clientY;pointer.drag=false;});
    renderer.domElement.addEventListener('pointermove',e=>{
      if(e.buttons!==1)return;
      const dx=e.clientX-pointer.x;
      if(Math.abs(dx)>3)pointer.drag=true;
      targetYaw+=dx*.012;pointer.x=e.clientX;
    });
    renderer.domElement.addEventListener('pointerup',e=>{
      if(!pointer.drag&&Math.abs(e.clientY-pointer.y)<12&&window.Companion) Companion.pet();
    });
    function resize(){
      const w=Math.max(1,innerWidth),h=Math.max(1,innerHeight);
      // WebView inside a Compose scroll container can resolve percentage height to zero.
      document.documentElement.style.height=h+'px'; document.body.style.height=h+'px';
      renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();
    }
    addEventListener('resize',resize);resize();
    let paused=false,last=0,frame=0;
    window.pauseCompanion=()=>{paused=true;}; window.resumeCompanion=()=>{paused=false;};
    function render(ms) {
      frame=requestAnimationFrame(render); if(paused||document.hidden||ms-last<32)return; last=ms;
      const t=ms/1000,elapsed=t-actionStart,active=elapsed<2.5;
      yaw+=(targetYaw-yaw)*.12; root.rotation.y=yaw;
      const growth=.90+(Math.min(state.level||1,10)-1)*.012;
      root.scale.setScalar(growth); root.position.y=0;
      head.rotation.set(Math.sin(t*.85)*.025,Math.sin(t*.53)*.07,Math.sin(t*.8)*.02);
      root.rotation.z=0; root.scale.y=growth*(1+Math.sin(t*2.1)*.014);
      arms.forEach(a=>a.rotation.z=0);
      if(tail)tail.rotation.y=Math.sin(t*2)*.17;
      const blink=Math.pow(Math.max(0,Math.sin(t*1.3)),40);
      eyes.forEach(e=>e.scale.y=state.sleeping?.10:Math.max(.08,1-blink*.94));
      if(state.sleeping){head.rotation.z=.16;head.rotation.x=.15;root.scale.y=growth*.91;}
      else if((state.energy||0)<.25){head.rotation.x=.12;eyes.forEach(e=>e.scale.y*=.6);}
      else if(state.joy<.3||state.hunger<.25) head.rotation.z=.1;
      dirt.forEach(p=>p.visible=state.clean<.4);
      bowl.visible=meal.visible=active&&animation==='feed'; toy.visible=active&&animation==='play';
      if(active&&!state.sleeping) {
        if(animation==='feed')head.rotation.x=.22+Math.sin(elapsed*9)*.09;
        if(animation==='play') {root.position.y=Math.abs(Math.sin(elapsed*5))*.24; root.rotation.z=Math.sin(elapsed*5)*.10; toy.position.x=Math.sin(elapsed*5)*.8;toy.position.y=.2+Math.abs(Math.cos(elapsed*5))*.22;}
        if(animation==='love') {head.rotation.z=Math.sin(elapsed*5)*.15; arms.forEach((a,i)=>a.rotation.z=(i===0?-1:1)*.5);}
        if(animation==='wash') {root.rotation.z=Math.sin(elapsed*9)*.045;}
      }
      particles.forEach((p,i)=>{
        p.visible=active&&(animation==='wash'||animation==='love');
        if(p.visible){const f=(elapsed*.5+i*.067)%1;p.position.set(Math.sin(i*2.4+elapsed)*(.5+f*.3),.5+f*2.4,.4+Math.cos(i)*.5);p.scale.setScalar((animation==='wash'?.12:.065)*(1-f*.6));}
      });
      renderer.render(scene,camera);
    }
    requestAnimationFrame(render);
    if(window.Companion) Companion.ready();
  }catch(e){report(e.message);}
})();
