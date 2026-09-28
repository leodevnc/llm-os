const {test,expect}=require('@playwright/test');

test('OS demo pages evidence, calculates, reviews a file, and releases memory',async({page})=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto('/');
  await expect(page.getByRole('heading',{name:'A small computer, driven by language.'})).toBeVisible();
  await expect(page.locator('#os-apps')).toContainText('Read-only reviewer');
  await page.screenshot({path:'docs/os-overview.png',fullPage:true});
  await page.getByRole('button',{name:'Run OS demo'}).click();
  await expect(page.getByRole('heading',{name:'Save this file?'})).toBeVisible();
  await expect(page.locator('#working-memory')).toContainText('Release checklist');
  await expect(page.locator('#approval')).toContainText('/reports/release-brief.md');
  await expect(page.locator('#approval')).toContainText('150');
  await page.evaluate(()=>window.scrollTo({top:0,behavior:'instant'}));
  await page.screenshot({path:'docs/os-working-memory.png',fullPage:true});
  await page.getByRole('button',{name:'Approve & continue'}).click();
  await expect(page.locator('#task-metrics')).toContainText('succeeded');
  await expect(page.locator('#task-metrics')).toContainText('6 / 10');
  await expect(page.locator('#working-memory')).toContainText('0 / 12,000');
  await expect(page.locator('#artifacts')).toContainText('/reports/release-brief.md');
  await page.getByRole('button',{name:/Files/}).first().click();
  await expect(page.locator('#os-files')).toContainText('150');
  await page.reload();
  await page.getByRole('button',{name:/Files/}).first().click();
  await expect(page.locator('#os-files')).toContainText('/reports/release-brief.md');
  await page.getByRole('button',{name:/Computer/}).first().click();
  await page.setViewportSize({width:390,height:844});
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.screenshot({path:'docs/os-mobile.png',fullPage:true});
  expect(errors).toEqual([]);
});

test('app launch requires a local model without silently running a demo',async({page})=>{
  await page.goto('/');
  await page.locator('.app-card').filter({hasText:'Read-only reviewer'}).getByRole('button',{name:'Open app'}).click();
  await expect(page.locator('#mode')).toHaveValue('ollama');
  await expect(page.locator('#app-id')).toHaveValue('reviewer');
  await expect(page.locator('#goal')).toBeEditable();
});
